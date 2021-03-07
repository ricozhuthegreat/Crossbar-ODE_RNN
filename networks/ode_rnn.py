
import torch
import torch.nn as nn

import crossbar.crossbar
import utils.linear as Linear
import utils.observer

import networks.ode_net

class ODE_RNN(nn.Module):

    def __init__(self, input_size, hidden_layer_size, output_size, device_params, time_steps):

        super(ODE_RNN, self).__init__()

        self.N = time_steps

        self.observer = observer.observer()
        self.cb = crossbar.crossbar(device_params)

        # Construct model and layers
        self.input_size = input_size
        self.linear_in = Linear.Linear(input_size, hidden_layer_size, self.cb)

        self.hidden_layer_size = hidden_layer_size
        self.linear_hidden = Linear.Linear(hidden_layer_size, hidden_layer_size, self.cb)

        self.output_size = output_size
        self.linear_out = Linear.Linear(hidden_layer_size, output_size, self.cb)

        self.solve = ODE_RNN(hidden_layer_size, time_steps, self.cb, self.observer)
        self.nonlinear = nn.Tanh()

    # Taking a sequence, this predicts the next N points, where
    def forward(self, x, t):

        h_i = torch.zeros(self.hidden_layer_size, 1)

        for i, x_i in enumerate(x):
            if i == (len(x) - 1) and self.observer.on == True:
                self.solve.observer_flag = True
            
            h_i = self.solve(h_i, t[i-1] if i>0 else t[i], t[i])
            
            if i == (len(x) - 1):
                self.observer.append(h_i.view(1, -1), t[i])

            h_i = self.nonlinear(self.linear_in(x_i) + self.linear_hidden(h_i))

            if i == (len(x) - 1):
                self.observer.append(h_i.view(1, -1), t[i])

            self.solve.observer_flag = False

        return h_i

    def remap(self):
        self.cb.clear()
        self.linear_in.remap()
        self.linear_hidden.remap()
        self.linear_out.remap()
    
    def use_cb(self, state):
        self.linear_in.use_cb(state)
        self.linear_hidden.use_cb(state)
        self.solve.use_cb(state)