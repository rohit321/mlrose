""" Classes for defining neural network weight optimization problems.

    Author: Genevieve Hayes 
    License: 3-clause BSD license.
"""
import numpy as np
from sklearn.metrics import mean_squared_error, log_loss
from activation import identity, relu, sigmoid, softmax, tanh
from algorithms import random_hill_climb, simulated_annealing, genetic_alg
from opt_probs import ContinuousOpt
from decay import GeomDecay

def flatten_weights(weights):
    """Flatten list of weights arrays into a 1D array.
    
    Args:
    weights: list of arrays. List of 2D arrays for flattening
    
    Returns:
    flat_weights: array. 1D weights array.
    """
    flat_weights = []
    
    for i in range(len(weights)):
        flat_weights += list(weights[i].flatten())
        
    flat_weights = np.array(flat_weights)
    
    return flat_weights
    
def unflatten_weights(flat_weights, node_list):
    """Convert 1D weights array into list of 2D arrays.
    
    Args:
    flat_weights: array. 1D weights array.
    node_list: list. List giving the number of nodes in each layer of the
    network, including the input and output layers.
    
    Returns:
    weights: list of arrays. List of 2D arrays created from flat_weights.
    """
    weights = []
    start = 0
    
    for i in range(len(node_list) - 1):
        end = start + node_list[i]*node_list[i + 1]
        weights.append(np.reshape(flat_weights[start:end],\
                        [node_list[i], node_list[i+1]]))
        start = end
    
    return weights

def gradient_descent(problem, max_attempts=10, max_iters=np.inf, 
                     init_state=None):
    """Use gradient_descent to find the optimal neural network weights
    
    Args:
    problem: Optimization class object. Object containing
    optimization problem to be solved.
    max_attempts: int. Maximum number of attempts to find a better state
    at each step.
    max_iters: int. Maximum number of iterations of the algorithm.
    init_state: array. Numpy array containing starting state for algorithm. 
    If None then a random state is used.

    Returns:
    best_state: array. NumPy array containing state that optimizes
    fitness function.
    best_fitness: float. Value of fitness function at best state.
    """
    # Initialize problem, time and attempts counter
    if init_state is None:
        problem.reset()
    else:
        problem.set_state(init_state)
        
    attempts = 0
    iters = 0
    
    best_fitness = problem.get_maximize()*problem.get_fitness()
    best_state = problem.get_state()

    
    while (attempts < max_attempts) and (iters < max_iters):
        iters += 1
        
        # Update weights
        updates = flatten_weights(problem.calculate_updates())
        
        next_state = problem.update_state(updates)
        next_fitness = problem.eval_fitness(next_state)
        
        if next_fitness > problem.get_fitness():
            attempts = 0
        else:
            attempts += 1
        
        if next_fitness > problem.get_maximize()*best_fitness:
            best_fitness = problem.get_maximize()*next_fitness
            best_state = next_state
            
        problem.set_state(next_state)

    return best_state, best_fitness

class NetworkWeights:
    """Fitness function for neural network weights optimization problem."""
    
    def __init__(self, X, y, node_list, activation, bias=True, 
                 is_classifier=True, learning_rate=0.1):
        
        """Initialize NetworkWeights object.

        Args:
        X: array. Numpy array containing feature dataset with each row 
        representing a single observation.
        y: array. Numpy array containing true values of data labels.
        Length must be same as length of X.
        node_list: list of ints. Number of nodes in each layer, including the
        input and output layers.
        activation: function. Activation function for each of the hidden 
        layers.
        bias: bool. Whether a bias term is included at each layer.
        is_classifer: bool. Whether the network is for classification or
        regression. Set True for classification and False for regression.
        
        Returns:
        None
        """
        self.X = X
        self.y_true = y
        self.node_list = node_list
        self.activation = activation
        self.bias = bias
        self.is_classifier = is_classifier
        self.lr = learning_rate
        
        # Determine appropriate loss function and output activation function
        if self.is_classifier:
            self.loss = log_loss
            
            if np.shape(self.y_true)[1] == 1: 
                self.output_activation = sigmoid
            else:
                self.output_activation = softmax
        else:
            self.loss = mean_squared_error
            self.output_activation = identity
        
        self.inputs_list = []
        self.y_pred = y
        self.weights = []        
        self.prob_type = 'continuous'

    def evaluate(self, state):
        """Evaluate the fitness of a state

        Args:
        state: array. State array for evaluation. Must contain the same number
        of elements as the distances matrix

        Returns:
        fitness: float. Value of fitness function.
        """
        self.inputs_list = []
        self.weights = unflatten_weights(state, self.node_list)
        
        # Add bias column to inputs matrix, if required
        if self.bias:
            ones = np.ones([np.shape(self.X)[0], 1])
            inputs = np.hstack((self.X, ones))
        
        else:
            inputs = self.X
            
        # Pass data through network    
        for i in range(len(self.weights)):
            # Multiple inputs by weights
            outputs = np.dot(inputs, self.weights[i])
            self.inputs_list.append(inputs)
            
            # Transform outputs to get inputs for next layer (or final preds)
            if i < len(self.weights) - 1:
                inputs = self.activation(outputs)
            else:
                self.y_pred = self.output_activation(outputs)       
        
        # Evaluate loss function
        fitness = self.loss(self.y_true, self.y_pred)
        
        return fitness
    
    def get_output_activation(self):
        """ Return the activation function for the output layer.
        
        Args:
        None

        Returns:
        self.output_activation: function. Activation function for the output 
        layer.
        """
        return self.output_activation
    
    def get_prob_type(self):
        """ Return the problem type

        Args:
        None

        Returns:
        self.prob_type: string. Specifies problem type as 'discrete',
        'continuous' or 'either'
        """
        return self.prob_type
        
    def calculate_updates(self):
        """Calculate gradient descent updates.
        
        Args:
        None
        
        Returns:
        updates_list: list. List of back propagation weight updates.
        """
        delta_list = []
        updates_list = []
        
        # Work backwards from final layer
        for i in range(len(self.inputs_list)-1, -1, -1):
            # Final layer
            if i == len(self.inputs_list)-1:
                delta = (self.y_pred - self.y_true)
            # Hidden layers
            else:
                delta = np.dot(delta_list[-1], 
                               np.transpose(self.weights[i+1]))*\
                               self.activation(self.inputs_list[i+1], 
                                               deriv=True)
            
            delta_list.append(delta)
            
            # Calculate updates
            updates = -1.0*self.lr*np.dot(np.transpose(self.inputs_list[i]),
                                          delta)
            
            updates_list.append(updates)
        
        # Reverse order of updates list
        updates_list = updates_list[::-1]
        
        return updates_list

class NeuralNetwork:
    """Class for defining neural network weights optimization problem."""
    
    def __init__(self, hidden_nodes, activation='relu', 
                 algorithm='random_hill_climb', max_iters=100, bias=True, 
                 is_classifier=True, learning_rate=0.1, early_stopping=False, 
                 clip_max=1e+10, schedule=GeomDecay(), pop_size=200, 
                 mutation_prob=0.1, max_attempts=10):        
        """Initialize NeuralNetwork object.

        Args:
        hidden_nodes: list of ints. List giving the number of nodes in each
        hidden layer.
        activation: function. Activation function for each of the hidden 
        layers. Must be one of: 'identity', 'relu', 'sigmoid' or 'tanh'.
        algorithm: string. Algorithm used to find optimal weights. Must be one
        of:'random_hill_climb', 'simulated_annealing', 'genetic_alg' or 
        'gradient_descent'.
        max_iters: int. Maximum number of iterations used to fit the weights.
        bias: bool. Whether to include a bias term at each layer.
        is_classifer: bool. Whether the network is for classification or
        regression. Set True for classification and False for regression.
        learning_rate: float. Learning rate for gradient descent or step size 
        for randomized optimization algorithms.
        early_stopping: bool. Whether to terminate algorithm early if the 
        loss is not improving. If True then stop after max_attempts iters with
        no improvement.
        clip_max: float. Used to limit weights to the range [-1*clip_max, 
        clip_max].
        schedule: Schedule class object. Schedule used to determine the value 
        of the temperature parameter. Only required for simulated annealing.
        pop_size: int. Size of population. Only required for genetic algorithm.
        mutation_prob: float. Probability of a mutation at each element during 
        reproduction. Only required for genetic algorithm.
        max_attempts: int. Maximum number of attempts to find a better state.
        Only required if early_stopping is True.
        
        Returns:
        None
        """
        self.hidden_nodes = hidden_nodes
        self.max_iters = max_iters
        self.bias = bias
        self.is_classifier = is_classifier
        self.lr = learning_rate
        self.early_stopping = early_stopping
        self.clip_max = clip_max
        self.schedule = schedule
        self.pop_size = pop_size
        self.mutation_prob = mutation_prob
        
        activation_dict = {'identity':identity, 'relu': relu, 
                           'sigmoid': sigmoid, 'tanh': tanh}
        if activation in activation_dict.keys():
            self.activation = activation_dict[activation]
        else:
            raise Exception("""Activation function must be one of: 'identity',
            'relu', 'sigmoid' or 'tanh'.""")
        
        if algorithm in ['random_hill_climb', 'simulated_annealing', 
                         'genetic_alg', 'gradient_descent']:
            self.algorithm = algorithm        
        else: 
            raise Exception("""Algorithm must be one of: 'random_hill_climb', 
            'simulated_annealing', 'genetic_alg', 'gradient_descent'.""")
            
        if self.early_stopping:
            self.max_attempts = max_attempts
        else:
            self.max_attempts = self.max_iters
        
        self.node_list = []
        self.fitted_weights = []
        self.loss = []
        self.output_activation = None
        
    def fit(self, X, y, init_weights = None):
        """Fit neural network to data.
        
        Args:
        X: array. Numpy array containing feature dataset with each row 
        representing a single observation.
        y: array. Numpy array containing data labels. Length must be same as
        length of X.
        init_state: array. Numpy array containing starting weights for 
        algorithm. If None then a random state is used.
        
        Returns:
        None
        """
        # Make sure y is an array and not a list
        y = np.array(y)
        
        # Convert y to 2D if necessary
        if len(np.shape(y)) == 1:
            y = np.reshape(y, [len(y), 1])
         
        # Verify X and y are the same length
        if not np.shape(X)[0] == np.shape(y)[0]:
            raise Exception('The length of X and y must be equal.')
        
        # Determine number of nodes in each layer
        input_nodes = np.shape(X)[1] + self.bias
        output_nodes = np.shape(y)[1]
        node_list = [input_nodes] + self.hidden_nodes + [output_nodes]

        num_nodes = 0
        
        for i in range(len(node_list) - 1):
            num_nodes += node_list[i]*node_list[i+1]       

        # Initialize optimization problem
        fitness = NetworkWeights(X, y, node_list, self.activation, self.bias,
                                 self.is_classifier, learning_rate = self.lr)

        problem = ContinuousOpt(num_nodes, fitness, maximize=False, 
                                min_val=-1*self.clip_max, 
                                max_val=self.clip_max, step=self.lr)
        
        if self.algorithm == 'random_hill_climb':
            if init_weights is None:
                init_weights = np.random.uniform(-1, 1, num_nodes)

            fitted_weights, loss = random_hill_climb(problem,
                max_attempts=self.max_attempts, max_iters=self.max_iters, 
                restarts=0, init_state=init_weights)
            
        elif self.algorithm == 'simulated_annealing':
            if init_weights is None:
                init_weights = np.random.uniform(-1, 1, num_nodes)
            fitted_weights, loss = simulated_annealing(problem,
                schedule=self.schedule, max_attempts=self.max_attempts, 
                max_iters=self.max_iters, init_state=init_weights)

        elif self.algorithm == 'genetic_alg':
            fitted_weights, loss = genetic_alg(problem, 
                pop_size=self.pop_size, mutation_prob=self.mutation_prob,
                max_attempts=self.max_attempts, max_iters=self.max_iters)

        else: # Gradient descent case
            if init_weights is None:
                init_weights = np.random.uniform(-1, 1, num_nodes)
            fitted_weights, loss = gradient_descent(problem, 
                max_attempts=self.max_attempts, max_iters=self.max_iters,
                init_state=init_weights)

        # Save fitted weights and node list
        self.node_list = node_list
        self.fitted_weights = fitted_weights
        self.loss = loss
        self.output_activation = fitness.get_output_activation()
   
    def predict(self, X):
        """Use model to predict data labels for given feature array.
        
        Args:
        X: array. Numpy array containing feature dataset with each row 
        representing a single observation.
        
        Returns:
        y_pred: array. Numpy array containing predicted data labels.
        """
        weights = unflatten_weights(self.fitted_weights, self.node_list)

        # Add bias column to inputs matrix, if required
        if self.bias:
            ones = np.ones([np.shape(X)[0], 1])
            inputs = np.hstack((X, ones))
        
        else:
            inputs = X
            
        # Pass data through network
        for i in range(len(weights)):
            # Multiple inputs by weights
            outputs = np.dot(inputs, weights[i])

            # Transform outputs to get inputs for next layer (or final preds)
            if i < len(weights) - 1:
                inputs = self.activation(outputs)
            else:
                y_pred = self.output_activation(outputs)       
        
        return y_pred
        