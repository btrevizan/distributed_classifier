import numpy
import copy

from data import Dataset
from learner import Learner
from sklearn import model_selection


class Simulator():
	"""Distributed classification learning simulator.

	Properties:
		learners -- a list of learners
	"""

	def __init__(self, learners):
		"""Sets the properties, create the agents, divides the data between the agents
		
		Keyword arguments:
			n_learners -- number of agents to be used (must be greater than 1)
		"""

		self.learners = learners

	@staticmethod
	def get_distribution(data, n, overlap=0):
		"""Not implemented. Should be implemented in a child class."""
		pass

	@classmethod
	def slice_data(data, n_learners, overlap=0):
		"""Vertically slices the data and returns a list of sliced data with length n_learners
		
		Keyword arguments:
			data -- the training set to be sliced (Data)
			n_learners -- number of learners
			overlap -- if float, should be between 0.0 and 1.0 and represents the percentage
					   of parts' in common. If int, should be less than or equal to the 
					   number of features/instances and represents the number of common 
					   features/instances. If list, represents the features'/instances' 
					   indexes. By default, the value is set to 0.
		"""

		# Gets the distributed indexes
		distribution = cls.get_distribution(data, n_learners, overlap)

		# Uses the indexes to slice the data for each learner
		return [Data(data.x[:, indexes], data.y) for indexes in distribution]

	@classmethod
	def load(cls, data, classifers, overlap=0, test_size=0.3):
		"""Creates n_learners Learner objects and returns a DistributedClassification object

		Keyword arguments:
			data -- a Data object or a list of Data objects with sliced data
			classifiers -- a list of classifiers, len(classifiers) define the number of learners
			overlap -- if float, should be between 0.0 and 1.0 and represents the percentage
					   of parts' in common. If int, should be less than or equal to the 
					   number of features/instances and represents the number of common 
					   features/instances. If list, represents the features'/instances' 
					   indexes. By default, the value is set to 0.
			test_size -- percent of test instances (default 0.3)
		"""

		# The number of classifiers define the number of learners
		n_learners = len(classifiers)

		# Checks the data variable type
		if type(data) is not list:
			# It means the data isn't sliced
			sliced_data = cls.slice_data(data, n_learners, overlap) # slices the data

		else:
			# It means the data is already sliced
			sliced_data = data

		# Initialize an empty list for learners
		learners = list()

		# For each part of the sliced data
		for i, data in enumerate(sliced_data):
			dataset = Dataset(data, test_size) 	   # creates a dataset for learner
			classifier = classifiers[i]			   # gets the classifier

			learner = Learner(dataset, classifier) # creates the learner
			learners.append(learner)			   # saves the learner

		# Creates a DistributedClassifition simulator
		return cls(learners)

	def cross_validate(self, k_fold=10, n_it=10):
		"""Not implemented. Should be implemented in a child class."""
		pass


class FeatureDistributed(Simulator):
	"""Feature distributed classification learning simulator.

	Description:
		This class simulates a distributed learning using classifier agents. It divides
		the data vertically, i. e., it divides the features randomly between the learners.

	Also see: Simulator class documentation.
	"""

	def __init__(self, learners):
		"""Sets the properties, create the agents, divides the data between the agents
		
		Keyword arguments:
			learners -- list of learners (lenght must be greater than 1)
		"""

		# Calls __init__ from parent
		super().__init__(learners)
		

	@staticmethod
	def get_distribution(data, n, overlap=0):
		"""Vertically distributes the training data into n parts and returns a list of
		column indexes for each part 

		Keyword arguments:
			data -- the training set to be splitted (Data)
			n -- number of divisions
			overlap -- if float, should be between 0.0 and 1.0 and represents the percentage
					   of parts' common features. If int, should be less than or equal to the 
					   number of features and represents the number of common features. If list, 
					   represents the features' columns indexes. By default, the value is set to 0.
		"""

		# Check the type of overlap variable and sets the n_common and common_features, where
		# n_common is the number of common features for each part and
		# common_features is a common features' index's list
		if type(overlap) is int:
			common_features = set(numpy.random.choice(data.n_features, overlap))  # gets a n length list with random numbers between 0-n_features
		
		elif type(overlap) is float:
			n_common = math.ceil(data.n_features * overlap)						  # calculates the amount of features each part has in common
			common_features = set(numpy.random.choice(data.n_features, n_common)) # gets a n length list with random numbers between 0-n_features
		
		elif type(overlap) is list:
			common_features = set(overlap)
		
		else: # is neither int, float and list
			raise TypeError("%s should be a float, an int or a list. %s given." % (str(overlap), type(overlap)))		

		# Calculates the distinct features' indexes
		distinct_features = list(set(range(data.n_features)) - common_features) # common_features' complement

		# Just converts from set to list
		common_features = list(common_features)

		# Permutates the distinct features (randomize)
		distinct_features = numpy.random.permutation(distinct_features)

		# Calculate the number of distinct features per part
		n_distinct = len(distinct_features)

		# Calculates the number of distinc features per part
		n_part_features = math.ceil(n_distinct / n)

		# Empty list for the loop
		distribution = []

		# The main object in the loop is the distinct_features list
		# We want to add a slice of this list with the common_features list
		# for each part
		for i in range(0, n_distinct + 1, n_part_features):
			j = i + n_part_features									# stop index for slice, garantees n features to the part
			part_indexes = common_features + distinct_features[i:j] # list of common and distinct indexes for the part
			distribution.append(part_indexes)						# adds the list to distribution

		# Returns the distribution list
		return distribution

	def cross_validate(self, k_fold=10, scoring=['accuracy', 'precision'], n_it=10):
		"""Runs the cross_validate function for each agent and returns a list with each learner's scores
		
		Keyword arguments:
			k_fold -- number of folds
			scoring -- metrics to be returned (default ['accuracy', 'precision'])*
			n_it -- number of cross-validation iterations (default 10, i. e., 10 k-fold cross-validation)
		
		*For more information about the returned data and the parameters: 
		http://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_validate.html
		"""

		# Gets a sample of the data for the splitter
		sample_x = self.learners[0].dataset.trainingset.x # instances
		sample_y = self.learners[0].dataset.trainingset.y # classes

		# Splits into k training and test folds for cross-validation
		skf = StratifiedKFold(n_splits=k_fold) # create the 'splitter' object 

		# The split works with a sample of the data because we *vertically* sliced it
		folds = skf.split(sample_x, sample_y)  # creates the folds

		# For each learner, runs its cross-validation function saves its score
		scores = [learner.cross_validate(folds, scoring, n_it) for learner in self.learners]

		# Returns the scores
		return scores


class InstanceDistributed(Simulator):
	"""Instance distributed classification learning simulator.

	Description:
		This class simulates a distributed learning using classifier agents. It divides
		the data horizontally, i. e., it divides the instances randomly between the learners.

	Also see: Simulator class documentation.
	"""

	def __init__(self, learners):
		"""Sets the properties, create the agents, divides the data between the agents
		
		Keyword arguments:
			learners -- list of learners (lenght must be greater than 1)
		"""

		# Calls __init__ from parent
		super().__init__(learners)

	@staticmethod
	def get_distribution(data, n, overlap=0):
		"""Vertically distributes the training data into n parts and returns a list of
		column indexes for each part 

		Keyword arguments:
			data -- the training set to be splitted (Data)
			n -- number of divisions
			overlap -- if float, should be between 0.0 and 1.0 and represents the percentage
					   of parts' common instances. If int, should be less than or equal to the 
					   number of instances and represents the number of common instances. If list, 
					   represents the instances' columns indexes. By default, the value is set to 0.
		"""
		
		pass

	def cross_validate(self, k_fold=10, n_it=10):
		"""Runs the cross_validate function for each agent and returns a list with each learner's scores
		
		Keyword arguments:
			k_fold -- number of folds
			n_it -- number of cross-validation iterations (default 10, i. e., 10 k-fold cross-validation)
		"""

		pass