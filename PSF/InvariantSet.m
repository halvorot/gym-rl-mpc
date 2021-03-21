function [PK] = InvariantSet(A_set,B_set, Hx, Hu, hx, hu)


Px = Polyhedron(Hx, hx);

x_center= Px.chebyCenter();
x_0 = x_center.x;
hx_0 =hx+Hx*x_0;


Pu= Polyhedron(Hu, hu);

u_center= Pu.chebyCenter();
u_0 = x_center.x;
hu_0 =hu- Hu*u_0;

x_0=Polyhedron(Hx,hx).chebyCenter().x
u_0=Polyhedron(Hu,hu).chebyCenter().x
Ao = [A A*x_0]
Ao(end+1,end)=1
Bo = [B B*u_0]
Bo(end+1,end)=1 

hx_0 = hx+Hx*x_0

Hx_0= Hx
Hx_0(end,end+1)=0

hu_0 = hu+Hu*u_0,0

Hu_0= Hu
Hu_0(end,end+1)=0



nx = size(Hx,2);
nu = size(Hu,2);

A_set = reshape(A_set,nx,nx,numel(A_set)/nx^2);

B_set = reshape(B_set,nx,nu,numel(B_set)/(nx*nu));


E = sdpvar(nx);
Y = sdpvar(nx,nu);


% --------- Start Modifying Code Here -----------
% Please use the provided variables

% Objective: Maximize ellipsoidal volume
objective = -logdet(E);

constraints = [];
% Constraints
% Positive Definite and Lyapunov Decrease
for k = 1:size(A_set,3)
    A = A_set(:,:,k);
    B = B_set(:,:,k);
    constraints= [constraints, [E, (A*E+B*Y)'; A*E+B*Y, E]>=0];
end

% State constraints
for i=1:size(Hx,1)
    constraints=[constraints, [hx_0(i)^2, Hx(i,:)*E; E*Hx(i,:)', E]>=0];
end
% Input constraints
for j=1:size(Hu,1)
    constraints=[constraints, [hu_0(j)^2, Hu(j,:)*Y;Y'*Hu(j,:)', E]>=0];
end
% --------- End Modifying Code Here -----------

% Solve
opts = sdpsettings('verbose',0,'solver','SDPT3');
optimize(constraints, objective,opts);   

% --------- Start Modifying Code Here -----------
P = inv(value(E));
K = value(Y)*P;
PK =[P,K];



xplot = sdpvar(3,1);
Pproj1 = YSet(xplot,xplot'*P*xplot <= 1);


figure()
hold off
plot(Px,'alpha',0.1);
hold on
plot(Pproj1,'alpha',0.1);
savefig(gcf,'Ellips.fig');
save("LastPK",'P','K',"Px");
u = PolyUnion([Pproj1.outerApprox,Px]);
if not(u.isConnected())
     disp()
     disp("WARNING")
     disp("The Ellipse Outer Approx is not connected to constrain polyhedron")
     disp()
end

