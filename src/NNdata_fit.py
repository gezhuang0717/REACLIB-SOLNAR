import numpy as np
import os
import matplotlib.pyplot as plt

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import layers
from tensorflow import keras
import tensorflow as tf
import tensorflow_probability as tfp


mae_loss = keras.losses.MeanAbsoluteError()


def reaclib_exp(t9, a0, a1, a2, a3, a4, a5, a6):
    """Rate format of REACLIB library.
    t9          : Temperature in Gigakelvin
    a0,...,a6   : Parameters of REACLIB function"""
    params = [a0, a1, a2, a3, a4, a5, a6]
    s = params[0]
    for i in range(1, 6):
        s += params[i]*t9**((2*i-5)/3)
    s += params[6]*np.log(t9)
    return s


def read_data(n, z):
    """Reads the data from ./data/{n}-{z}/, and outputs a (Q, T)-array and Rate list, as fit dataset.
    n       : neutron number
    z       : proton number"""

    dir_path = f"./data/{z}-{n}/"
    files = os.listdir(dir_path)
    files.sort()

    QT_points = [[] for i in range(0, 6)]
    rate_points = [[] for i in range(0, 6)]
    templist = []
    qlist = []

    for file_path in files:
        Q, idx, ld_idx = float(file_path.split("|")[1]), int(file_path.split("|")[2]), int(file_path.split("|")[3])
        with open(dir_path + file_path, "r") as f:
            f.readline()
            f.readline()
            f.readline()
            line = line.split(" ")
            temperature, rate = float(line[2]), float(line[3])
            QT_points[ld_idx].append((Q, temperature))
            rate_points[ld_idx].append(rate)
            templist.append(temperature)
            qlist.append(Q)
            while True:
                line = f.readline()
                if not line or "Q" in line:
                    break
                line = line.split(" ")
                temperature, rate = float(line[2]), float(line[3])
                QT_points[ld_idx].append((Q, temperature))
                rate_points[ld_idx].append(rate)

    # these arrays need to be flattened or select one of the dimensions (different LD models)
    return np.array(QT_points), np.array(rate_points), qlist, templist[0:108]



def prior(kernel_size, bias_size, dtype=None):
    n = kernel_size + bias_size
    prior_model = keras.Sequential([tfp.layers.DistributionLambda(
        lambda t: tfp.distributions.MultivariateNormalDiag(
            loc=tf.zeros(n), scale_diag=tf.ones(n)
        )
    )])
    return prior_model

def posterior(kernel_size, bias_size, dtype=None):
    n = kernel_size + bias_size
    posterior_model = keras.Sequential([tfp.layers.VariableLayer(
        tfp.layers.MultivariateNormalTriL.params_size(n), dtype=dtype),
        tfp.layers.MultivariateNormalTriL(n)])
    return posterior_model


def create_probabilistic_bnn_model(train_size):

    model = keras.Sequential([keras.layers.Input(shape=(2,)),
        tfp.layers.DenseVariational(
                units=4,
                make_prior_fn=prior,
                make_posterior_fn=posterior,
                kl_weight=1 / train_size,
                activation="sigmoid",),
        tfp.layers.DenseVariational(
                units=4,
                make_prior_fn=prior,
                make_posterior_fn=posterior,
                kl_weight=1 / train_size,
                activation="sigmoid",),
        layers.Dense(units=2),
        tfp.layers.IndependentNormal(1)])

    return model


def create_bnn_model(train_size):

    model = keras.Sequential([keras.layers.Input(shape=(2,)),
        tfp.layers.DenseVariational(
                units=4,
                make_prior_fn=prior,
                make_posterior_fn=posterior,
                kl_weight=1 / train_size,
                activation="sigmoid",),
        tfp.layers.DenseVariational(
                units=4,
                make_prior_fn=prior,
                make_posterior_fn=posterior,
                kl_weight=1 / train_size,
                activation="sigmoid",),
        layers.Dense(units=1)])

    return model


def create_standard_nn_model(train_size):

    model = keras.Sequential([keras.layers.Input(shape=(2,)),
        layers.Dense(
                units=4,
                activation="sigmoid"),
        layers.Dense(
                units=4,
                activation="sigmoid"),
        layers.Dense(units=1)])

    return model


def negative_loglikelihood(targets, estimated_distribution):
    """Loss function of negative log-likelihood."""
    return -estimated_distribution.log_prob(targets)


def fit_data(model, loss, QT_array, rate_array, train_size, batch_size):
    """Fits the NN model to the rate surface provided.
    model       : NN model to be used for the fit
    loss        : loss function to be used
    QT_array    : array of (Q, T) points of rates
    rate_array  : array of rates for (Q, T) points
    train_size  : number of data points
    batch_size  : batch size"""
    
    train_size = 108*21*6
    batch_size = 32
    epochs = 1200

    initial_learning_rate = 0.1
    final_learning_rate = 0.00075
    learning_rate_decay_factor = (final_learning_rate / initial_learning_rate)**(1/epochs)
    steps_per_epoch = int(train_size/batch_size)

    # exponential decay learning rate
    lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
                initial_learning_rate=initial_learning_rate,
                decay_steps=steps_per_epoch,
                decay_rate=learning_rate_decay_factor,
                staircase=True)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr_schedule),
        loss=loss,
        metrics=[keras.metrics.RootMeanSquaredError()],
    )

    return None


def plot_probabilistic_bnn(model, n, z, Q=None, q_idx=None, rate_data=None, templist=None):

    if q_idx and rate_data and templist:
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1)
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1)
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1)
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1)
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1)
        plt.plot(templist, np.log10(2**(rate_data[0, q_idx, :])), color="red", linewidth=1, label="TALYS Data")

    if Q:
        tempsLin = np.arange(0.0001, 10, 0.03)
        plotarray = [(Q, t) for t in tempsLin]
        #for _ in range(iterations):
        #   plt.plot(tempsLin, (model.predict(plotarray)), color="green")
        prediction_distribution = model(np.array(plotarray))
        prediction_mean = prediction_distribution.mean().numpy()
        prediction_stdv = prediction_distribution.stddev().numpy()

        plt.plot(tempsLin, np.log10(2**prediction_mean), color="royalblue", label="Mean Fit, μ")
        plt.fill_between(tempsLin, (np.log10(2**(prediction_mean + prediction_stdv))).flatten(), (np.log10(2**(prediction_mean - prediction_stdv))).flatten(), color="lightsteelblue", label="μ±σ")

    plt.title(f"Reaction Rate vs. Temperature for {n=},{z=} and Q={Q} MeV")
    plt.xlabel("Temperature [GK]")
    plt.ylabel("log10 Reaction rate")
    plt.legend()
    plt.savefig("constQ.png")
    plt.clf()


def plot_bnn(model, n, z, iterations=100, ld_idx=None, Q=None, q_idx=None, rate_data=None, templist=None):

    if ld_idx and q_idx and rate_data and templist:
        plt.plot(templist, np.log10(2**(rate_data[ld_idx, q_idx, :])), color="red", linewidth=1, label="TALYS Data")

    if Q:
        tempsLin = np.arange(0.0001, 10, 0.03)
        plotarray = [(Q, t) for t in tempsLin]
        for _ in range(iterations):
           plt.plot(tempsLin, (model.predict(plotarray)), color="lightsteelblue", label="BNN Predictions")

    plt.title(f"Reaction Rate vs. Temperature for {n=},{z=} and Q={Q} MeV")
    plt.xlabel("Temperature [GK]")
    plt.ylabel("log10 Reaction rate")
    plt.legend()
    plt.savefig("constQ.png")
    plt.clf()


def plot_standard_nn(model, n, z, ld_idx=None, Q=None, q_idx=None, rate_data=None, templist=None):

    if ld_idx and q_idx and rate_data and templist:
        plt.plot(templist, np.log10(2**(rate_data[ld_idx, q_idx, :])), color="red", linewidth=1, label="TALYS Data")

    if Q:
        tempsLin = np.arange(0.0001, 10, 0.03)
        plotarray = [(Q, t) for t in tempsLin]
        plt.plot(tempsLin, (model.predict(plotarray)), color="royalblue", label="NN Predictions")

    plt.title(f"Reaction Rate vs. Temperature for {n=},{z=} and Q={Q} MeV")
    plt.xlabel("Temperature [GK]")
    plt.ylabel("log10 Reaction rate")
    plt.legend()
    plt.savefig("constQ.png")
    plt.clf()


def save_probabilistic_bnn(model):
    pass


def save_bnn(model):
    pass


def save_standard_nn(model):
    pass


def load_probabilistic_bnn(model):
    pass


def load_bnn(model):
    pass


def load_standard_nn(model):
    pass


def reaclib_fit(model):
    pass


def main():
    """Just have to figure out what to put here :P"""

print(read_data(123, 82))