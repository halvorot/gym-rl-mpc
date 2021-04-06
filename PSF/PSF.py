import itertools
import pickle
from hashlib import sha1
from pathlib import Path

import numpy as np
from casadi import SX, Function, vertcat, inf, nlpsol, jacobian, mpower, qpsol, vertsplit, integrator

LEN_FILE_STR = 20


class PSF:
    def __init__(self,
                 sys,
                 N,
                 T,
                 R=None,
                 Q=None,
                 PK_path="",
                 param=None,
                 lin_bounds=None,
                 alpha=0.9,
                 slew_rate=None,
                 ext_step_size=1,
                 disc_method="RK",
                 LP_flag=False,
                 slack_flag=True,
                 jit_flag=False,
                 mpc_flag=False):

        if LP_flag:
            raise NotImplementedError("Linear MPC is not implemented")

        self.jit_flag = jit_flag
        self.slack_flag = slack_flag
        self.mpc_flag = mpc_flag

        self.LP_flag = LP_flag

        self.sys = sys
        self.Ac = jacobian(self.sys["xdot"], self.sys["x"])
        self.Bc = jacobian(self.sys["xdot"], self.sys["u"])

        self.N = N
        self.T = T
        self.alpha = alpha

        self.lin_bounds = lin_bounds

        self.PK_path = PK_path
        self.nx = self.sys["x"].shape[0]
        self.nu = self.sys["u"].shape[0]
        self.np = self.sys["p"].shape[0]

        self.slew_rate = slew_rate
        self.ext_step_size = ext_step_size

        self._centroid_Px = np.zeros((self.nx, 1))
        self._centroid_Pu = np.zeros((self.nu, 1))
        self._init_guess = np.array([])

        self.model_step = None
        self._sym_model_step = None
        self.problem = None
        self.eval_w0 = None
        self.solver = None

        if param is None:
            self.param = SX([])
        else:
            self.param = param

        self.Q = Q
        if R is None:
            self.R = np.eye(self.nu)
        else:
            self.R = R

        self.set_terminal_set()

        self.set_model_step(disc_method)
        self.formulate_problem()
        self.set_solver()

    def create_system_set(self):
        A_set = []
        B_set = []

        free_vars = SX.get_free(Function("list_free_vars", [], [self.Ac, self.Bc]))
        bounds = [self.lin_bounds[k.name()] for k in free_vars]  # relist as given above
        eval_func = Function("eval_func", free_vars, [self.Ac, self.Bc])

        for product in itertools.product(*bounds):  # creating maximum difference
            AB_set = eval_func(*product)
            A_set.append(np.asarray(AB_set[0]))
            B_set.append(np.asarray(AB_set[1]))

        return A_set, B_set

    def set_terminal_set(self):

        A_set, B_set = self.create_system_set()
        s = str((A_set, B_set, self.sys["Hx"], self.sys["Hu"], self.sys["hx"], self.sys["Hx"], self.ext_step_size))
        filename = sha1(s.encode()).hexdigest()[:LEN_FILE_STR]
        path = Path(self.PK_path, filename + ".dat")
        try:
            load_tuple = pickle.load(open(path, mode="rb"))
            self.K, self.P, self._centroid_Px, self._centroid_Pu = load_tuple
        except FileNotFoundError:
            print("Could not find stored KP, using MATLAB.")
            import matlab.engine

            Hx = matlab.double(self.sys["Hx"].tolist())
            hx = matlab.double(self.sys["hx"].tolist())
            Hu = matlab.double(self.sys["Hu"].tolist())
            hu = matlab.double(self.sys["hu"].tolist())

            m_A = matlab.double(np.hstack(A_set).tolist())
            m_B = matlab.double(np.hstack(B_set).tolist())

            eng = matlab.engine.start_matlab()
            eng.eval("addpath(genpath('./'))")
            P, K, centroid_Px, centroid_Pu = eng.terminalSet(m_A, m_B, Hx, Hu, hx, hu, self.ext_step_size, nargout=4)
            eng.quit()

            self.P = np.asarray(P)
            self.K = np.asarray(K)
            self._centroid_Px = np.asarray(centroid_Px)
            self._centroid_Pu = np.asarray(centroid_Pu)
            dump_tuple = (self.K, self.P, self._centroid_Px, self._centroid_Pu)
            pickle.dump(dump_tuple, open(path, "wb"))

    def set_cvodes_model_step(self):

        """
        dae = {'x': self.sys["x"], 'p': vertcat(self.sys["u"], self.sys["p"]), 'ode': self.sys["xdot"]}
        opts = {'tf': self.T / self.N, "expand": False}
        self._sym_model_step = integrator('F_internal', 'cvodes', dae, opts)

        def parse_model_step(xk, u, p, u_lin, x_lin):
            return self._sym_model_step(x0=xk, p=vertcat(u, p))

        self.model_step = parse_model_step
        """
        raise NotImplementedError("BUG. Waiting on forum answer: "
                                  "https://groups.google.com/g/casadi-users/c/hQG3zs88wVA")

    def set_taylor_model_step(self):

        M = 2
        DT = self.T / self.N
        Ad = np.eye(self.nx)
        Bd = 0
        for i in range(1, M):
            Ad += 1 / np.math.factorial(i) * mpower(self.Ac, i) * DT ** i
            Bd += 1 / np.math.factorial(i) * mpower(self.Ac, i - 1) * DT ** i

        Bd = Bd * self.Bc

        X0 = SX.sym('X0', self.nx)
        U = SX.sym('U', self.nu)
        X_next = Ad @ X0 + Bd @ U

        self._sym_model_step = Function('F',
                                        [X0, self.sys["x"], U, self.sys["u"], self.sys["p"]],
                                        [X_next],
                                        ['xk', 'x_lin', 'u', 'u_lin', 'p'],
                                        ['xf']
                                        )

        def parse_model_step(xk, u, p, u_lin, x_lin):
            return self._sym_model_step(xk=xk, x_lin=x_lin, u=u, u_lin=u_lin, p=p)

        self.model_step = parse_model_step

    def set_RK_model_step(self):
        M = 4  # RK4 steps per interval
        DT = self.T / self.N / M
        f = Function('f',
                     [self.sys["x"], self.sys["u"], self.sys["p"]],
                     [self.sys["xdot"]])
        Xk = SX.sym('Xk', self.nx)
        U = SX.sym('U', self.nu)
        P = SX.sym('P', self.np)
        X_next = Xk

        for j in range(M):
            k1 = f(X_next, U, P)
            k2 = f(X_next + DT / 2 * k1, U, P)
            k3 = f(X_next + DT / 2 * k2, U, P)
            k4 = f(X_next + DT * k3, U, P)
            X_next = X_next + DT / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

        self._sym_model_step = Function('F', [Xk, U, P], [X_next], ['xk', 'u', 'p'], ['xf'])

        def parse_model_step(xk, u, p, u_lin, x_lin):
            return self._sym_model_step(xk=xk, u=u, p=p)

        self.model_step = parse_model_step

    def set_model_step(self, method_name):
        if method_name == "RK":
            self.set_RK_model_step()
        elif method_name == "taylor":
            self.set_taylor_model_step()
        elif method_name == "cvodes":
            self.set_cvodes_model_step()
        else:
            raise ValueError(f"{method_name} is not a implemented method")

    def set_solver(self):

        if self.LP_flag:
            lin_points = [*vertsplit(self.sys["x"]), *vertsplit(self.sys["u"]), *vertsplit(self.sys["p"])]

            opts = {"osqp": {"verbose": 0, "polish": False}}
            self.solver = qpsol("solver", "osqp", self.problem, opts)
        else:
            # JIT
            # Pick a compiler
            # compiler = "gcc"  # Linux
            # compiler = "clang"  # OSX
            compiler = "cl.exe"  # Windows

            flags = ["/O2"]  # win
            jit_options = {"flags": flags, "verbose": True, "compiler": compiler}

            # JIT
            opts = {
                "warn_initial_bounds": True,
                "error_on_fail": True,
                "eval_errors_fatal": True,
                "verbose_init": False,
                "show_eval_warnings": False,
                "ipopt": {"print_level": 0, "sb": "yes"},
                "print_time": False,
                "compiler": "shell",
                "jit": self.jit_flag,
                'jit_options': jit_options
            }

            self.solver = nlpsol("solver", "ipopt", self.problem, opts)

    def formulate_problem(self):

        x0 = SX.sym('x0', self.nx, 1)

        X = SX.sym('X', self.nx, self.N + 1)
        x_ref = SX.sym('x_ref', self.nx, 1)

        U = SX.sym('U', self.nu, self.N)
        u_ref = SX.sym('u_ref', self.nu, 1)

        p = SX.sym("p", self.np, 1)

        u_stable = SX.sym('u_stable', self.nu, 1)
        u_prev = SX.sym('u_prev', self.nu, 1)

        eps = SX.sym("eps", self.nx, self.N)

        objective = self.get_objective(X=X, x_ref=x_ref, U=U, u_ref=u_ref, eps=eps)

        # empty problem
        w = []
        w0 = []

        g = []
        self.lbg = []
        self.ubg = []

        w += [X[:, 0]]
        w0 += [x0]

        g += [x0 - X[:, 0]]
        self.lbg += [0] * self.nx
        self.ubg += [0] * self.nx

        for i in range(self.N):
            w += [U[:, i]]
            w0 += [u_stable]
            # Composite Input constrains

            g += [self.sys["Hu"] @ U[:, i]]
            self.lbg += [-inf] * g[-1].shape[0]
            self.ubg += [self.sys["hu"]]

            w += [X[:, i + 1]]
            tmp_x0 = x0
            for j in range(i + 1):
                tmp_x0 = self.model_step(xk=tmp_x0, x_lin=tmp_x0, u=self.K @ tmp_x0, u_lin=self.K @ tmp_x0, p=p)["xf"]
            w0 += [tmp_x0]
            # Composite State constrains
            g += [self.sys["Hx"] @ X[:, i + 1]]
            self.lbg += [-inf] * g[-1].shape[0]
            self.ubg += [self.sys["hx"]]
            if self.slack_flag:
                w += [eps[:, i]]
                w0 += [0] * self.nx
                g += [X[:, i + 1] - self.model_step(xk=X[:, i], x_lin=x0, u=U[:, i], u_lin=u_stable, p=p)['xf'] + eps[:,
                                                                                                                  i]]
            else:
                g += [X[:, i + 1] - self.model_step(xk=X[:, i], x_lin=x0, u=U[:, i], u_lin=u_stable, p=p)["xf"]]
            # State propagation

            self.lbg += [0] * g[-1].shape[0]
            self.ubg += [0] * g[-1].shape[0]

        if self.slew_rate is not None:

            g += [U[:, 0] - u_prev]
            self.lbg += [-np.array(self.slew_rate) * self.ext_step_size]
            self.ubg += [np.array(self.slew_rate) * self.ext_step_size]

            DT = self.T / self.N
            for i in range(self.N - 1):
                g += [U[:, i + 1] - U[:, i]]
                self.lbg += [-np.array(self.slew_rate) * DT]
                self.ubg += [np.array(self.slew_rate) * DT]

        # Terminal Set constrain

        XN_shifted = X[:, self.N] - self._centroid_Px
        g += [XN_shifted.T @ self.P @ XN_shifted - [self.alpha]]
        self.lbg += [-inf]
        self.ubg += [0]

        self.eval_w0 = Function("eval_w0", [x0, u_ref, u_stable, p], [vertcat(*w0)])

        self.problem = {'f': objective, 'x': vertcat(*w), 'g': vertcat(*g), 'p': vertcat(x0, x_ref, u_ref, u_prev, p)}

    def reset_init_guess(self):
        self._init_guess = np.array([])

    def calc(self, x, u_L, u_stable, ext_params, u_prev=None, x_ref=None, reset_x0=False, ):

        if u_prev is None and self.slew_rate is not None:
            raise ValueError("'u_prev' must be set if 'slew_rate' is given")

        if u_prev is None:
            u_prev = u_L  # Dont care, just for vertcat match
        if x_ref is None:
            x_ref = [0] * self.nx
        if self._init_guess.shape[0] == 0:
            self._init_guess = np.asarray(self.eval_w0(x, u_L, u_stable, ext_params))

        solution = self.solver(p=vertcat(x, x_ref, u_L, u_prev, ext_params),
                               lbg=vertcat(*self.lbg),
                               ubg=vertcat(*self.ubg),
                               x0=self._init_guess
                               )
        if not reset_x0:
            prev = np.asarray(solution["x"])
            self._init_guess = prev

        return np.asarray(solution["x"][self.nx:self.nx + self.nu]).flatten()

    def get_objective(self, U=None, eps=None, x_ref=None, X=None, u_ref=None):

        if self.mpc_flag:
            objective = (x_ref - X)[:].T @ self.Q @ (x_ref - X)[:]
            if u_ref is not None:
                objective += (u_ref - U)[:].T @ self.R @ (u_ref - U)[:]
        else:
            objective = (u_ref - U[:, 0]).T @ self.R @ (u_ref - U[:, 0])
        if self.slack_flag:
            objective += objective + 10e9 * eps[:].T @ eps[:]
        return objective


if __name__ == '__main__':
    pass
