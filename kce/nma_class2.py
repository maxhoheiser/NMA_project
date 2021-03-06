import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import csv
import scipy.stats as st
import platform
import os, csv
from os import path
from numba import jit
from scipy import sparse
from scipy.sparse import csr_matrix
from scipy.interpolate import interp1d
from sklearn.decomposition import TruncatedSVD
import scipy.stats as st
import platform
from matplotlib import animation

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
import requests
import hashlib


"""
Class for all the functions from Samuel, Kcenia and Max NMA Projekt


"""

class glm():
    """[class to perform glm with]

    Returns:
        [type]: [description]
    """    
    def __init__(self):
        pass

    # helper functions ===============================================================
    def get_datamatrix(self, main_folder, all_session_folders, 
                        all_session_names, areas_selected, window_correction, 
                        subselect_area=False, window=2.5, event='stim time', to_pca=20):
        # create X_glm data matrix
        X_glm_all = None
        # create x matrix for glm
        y_glm_all = None

        # impot loader clas
        import loader
        # initialize loader object
        loader_obj = loader(main_folder)

        import pca
        pac = pca()

        for folder, name in zip(all_session_folders, all_session_names):

            # load session ================================================================
            session = loader_obj.load_session(folder, fast=True, update=False)
            
            # select dataframes and clean up ===========
            spikes_df = session['spikes_df']
            clusters_df = session['clusters_df']
            # drop bad clusters
            clusters_df.drop(clusters_df[clusters_df['label']=='bad'].index, axis=0, inplace=True)
            trials_df = session['trials_df']
            # drop not included trials
            trials_df.drop(trials_df[~trials_df['included']].index, axis=0, inplace=True)
            trials_df.drop('included', axis=1, inplace=True)
            # insert trial length
            trials_df.insert(7, 'trial length', (trials_df['end time']-trials_df['start time']) )
            

            
            # Principal Component Analysis==================================================
            # all visual areas
            if subselect_area:
                neuron_selector = clusters_df['recording area'].isin(areas_selected)

            else:
                # all neurons
                #neuron_selector = np.full(clusters_df.shape[0], True)
                spikes = clusters_df[neuron_selector]['spikes']

            if len(spikes) != 0:

                # select only trials which have a visual stimulus
                trials_selector = np.logical_or(trials_df['stim contrast left']!=0, trials_df['stim contrast right']!=0)
                trials = trials_df[trials_selector]
                # remove trials where stim is at both
                sub_selector = ~np.logical_and(trials['stim contrast left']==1, trials['stim contrast right']==1)
                trials= trials[sub_selector]

                ev_bevore = trials[event]+window_correction

                # get data matrix
                # get all spikes event-windw< < event+window
                X_pca = pca.get_data_matrix(ev_bevore, spikes, window)

                # perform PCA
                score, evectors, evals = pca.pca(X_pca)

                # GLM =========================================================================
                # prepare data for linear model
                # visual stimulus side
                # left = 0
                # right = 1
                y_glm = trials['stim contrast right'] #these are the binary choices the animal made on each trial (trialnr)
                
                # create data matrix
                X_glm = score[:,:to_pca] #these are the principal components first 30 across all subselected trials (trialnr x pcs)

                # add X_glm and y_glm to overall data matrix
                # concatenate X_glm_all with X_glm
                if X_glm_all is None:
                    X_glm_all = X_glm
                else:
                    X_glm_all = np.append(X_glm_all, X_glm, axis=0)

                # concatenate y_glm_all with y_glm
                if y_glm_all is None:
                    y_glm_all = y_glm
                else:
                    y_glm_all = np.append(y_glm_all, y_glm, axis=0)
                
            print(f"finished session{name}")
        return X_glm_all, y_glm_all


    def sigmoid(self, z):
        return 1 / (1+np.exp(-z))

    def model_selection(self, X, y, C_values, CV_values):
        """Compute CV accuracy for each C value.

        Args:
        X (2D array): Data matrix
        y (1D array): Label vector
        C_values (1D array): Array of hyperparameter values

        Returns:
        accuracies (1D array): CV accuracy with each value of C

        """
        accuracies_all = []

        for CV in CV_values:

            accuracies = []

            for C in C_values:

                # Initialize and fit the model
                model = LogisticRegression(penalty='l2',C=C, solver='lbfgs',max_iter=5000)
                model.fit(X,y)

                # Get the accuracy for each test split
                accs = cross_val_score(model,X,y,cv=int(CV))

                # Store the average test accuracy for this value of C
                accuracies.append(np.mean(accs))

            accuracies_all.append(accuracies)

        return accuracies_all

   # ploting functions ==============================================================
    def plot_weights(self, models, sharey=True):
        """Draw a stem plot of weights for each model in models dict."""
        n = len(models)
        fig = plt.figure(figsize=(10, 2.5 * n))
        axs = f.subplots(n, sharex=True, sharey=sharey)
        axs = np.atleast_1d(axs)
        for ax, (title, model) in zip(axs, models.items()):
            ax.margins(x=.02)
            stem = ax.stem(model.coef_.squeeze(), use_line_collection=True)
            stem[0].set_marker(".")
            stem[0].set_color(".2")
            stem[1].set_linewidths(.5)
            stem[1].set_color(".2")
            stem[2].set_visible(False)
            ax.axhline(0, color="C3", lw=3)
            ax.set(ylabel="Weight", title=title)
        ax.set(xlabel="Neuron (a.k.a. feature)")
        fig.tight_layout()
        return fig, axs


    def plot_function(self, f, name, var, points=(-10, 10)):
        """Evaluate f() on linear space between points and plot.

        Args:
        f (callable): function that maps scalar -> scalar
        name (string): Function name for axis labels
        var (string): Variable name for axis labels.
        points (tuple): Args for np.linspace to create eval grid.
        """
        x = np.linspace(*points)
        ax = plt.figure().subplots()
        ax.plot(x, f(x))
        ax.set(
        xlabel=f'${var}$',
        ylabel=f'${name}({var})$'
        )
        return ax

    def plot_model_selection(self, C_values, accuracies):
        """Plot the accuracy curve over log-spaced C values."""
        ax = plt.figure().subplots()
        ax.set_xscale("log")
        ax.plot(C_values, accuracies, marker="o")
        best_C = C_values[np.argmax(accuracies)]
        ax.set(
        xticks=C_values,
        xlabel="$C$",
        ylabel="Cross-validated accuracy",
        title=f"Best C: {best_C:1g} ({np.max(accuracies):.2%})",
        )
        return ax

    def plot_non_zero_coefs(self, C_values, non_zero_l1, n_voxels):
        """Plot the accuracy curve over log-spaced C values."""
        ax = plt.figure().subplots()
        ax.set_xscale("log")
        ax.plot(C_values, non_zero_l1, marker="o")
        ax.set(
        xticks=C_values,
        xlabel="$C$",
        ylabel="Number of non-zero coefficients",
        )
        ax.axhline(n_voxels, color=".1", linestyle=":")
        ax.annotate("Total\n# Neurons", (C_values[0], n_voxels * .98), va="top")
        return ax
   




# ===============================================================================================================================================


class pca():
    """[class to perform PCA with]

    Returns:
        [type]: [description]
    """    
    def __init__(self):
        pass


   # helper functions ==================================================================
    def get_data_matrix(self, trials_df, clusters_df, window):
        """get data matrix of mean firing around event given neurons and trials [trials, ]

        Args:
            trials_df (dataframe column): pandas series with spike times for each neuron 
            clusters_df (dataframe column): pandas series with event times for each trial
            window (float): window to compute firing rate for event_time-window < firing rate < event_time+window

        Returns:
            [type]: [description]
        """        
        # initialize data matrix X
        X = np.zeros([trials_df.shape[0], clusters_df.shape[0]])
        # running index for column = neuron
        X_j = 0
        for row in clusters_df:
            # running index for row = trial
            X_i = 0
            for trial in trials_df:
                start = trial-window
                stop = trial+window
                X[X_i,X_j] = np.sum( np.logical_and(row >= start, row <= stop)  )
                X_i += 1
            X_j += 1
        return X

    def change_of_basis(self, X, W):
        """
        Projects data onto a new basis.
        Args:
            X (numpy array of floats) : Data matrix each column corresponding to a
                                        different random variable
            W (numpy array of floats) : new orthonormal basis columns correspond to
                                        basis vectors
        Returns:
            (numpy array of floats)   : Data matrix expressed in new basis
        """
        Y = np.matmul(X, W)
        return Y

    def get_sample_cov_matrix(self, X):
        """
        Returns the sample covariance matrix of data X.
        Args:
            X (numpy array of floats) : Data matrix each column corresponds to a
                                        different random variable
        Returns:
            (numpy array of floats)   : Covariance matrix
        """
        X = X - np.mean(X, 0)
        cov_matrix = 1 / X.shape[0] * np.matmul(X.T, X)
        return cov_matrix


    def sort_evals_descending(self, evals, evectors):
        """
        Sorts eigenvalues and eigenvectors in decreasing order. Also aligns first two
        eigenvectors to be in first two quadrants (if 2D).
        Args:
            evals (numpy array of floats)    :   Vector of eigenvalues
            evectors (numpy array of floats) :   Corresponding matrix of eigenvectors
                                                each column corresponds to a different
                                                eigenvalue
        Returns:
            (numpy array of floats)          : Vector of eigenvalues after sorting
            (numpy array of floats)          : Matrix of eigenvectors after sorting
        """
        index = np.flip(np.argsort(evals))
        evals = evals[index]
        evectors = evectors[:, index]
        if evals.shape[0] == 2:
            if np.arccos(np.matmul(evectors[:, 0], 1 / np.sqrt(2) * np.array([1, 1]))) > np.pi / 2:
                evectors[:, 0] = -evectors[:, 0]
            if np.arccos(np.matmul(evectors[:, 1], 1 / np.sqrt(2)*np.array([-1, 1]))) > np.pi / 2:
                evectors[:, 1] = -evectors[:, 1]
        return evals, evectors

    def pca(self, X):
        """
        Performs PCA on multivariate data. Eigenvalues are sorted in decreasing order
        Args:
            X (numpy array of floats) :   Data matrix each column corresponds to a
                                        different random variable
        Returns:
            scores (numpy array of floats)    : Data projected onto the new basis
            evectors (numpy array of floats)    : Vector of eigenvalues
            evals (numpy array of floats)    : Corresponding matrix of eigenvectors
        """
        X = X - np.mean(X, 0)
        cov_matrix = self.get_sample_cov_matrix(X)
        evals, evectors = np.linalg.eigh(cov_matrix)
        evals, evectors = self.sort_evals_descending(evals, evectors)
        score = np.matmul(X, evectors)
        return score, evectors, evals

    def get_variance_explained(self, evals):
        """
        Calculates variance explained from the eigenvalues.
        Args:
            evals (numpy array of floats) : Vector of eigenvalues
        Returns:
            (numpy array of floats)       : Vector of variance explained
        """
        # cumulatively sum the eigenvalues
        csum = np.cumsum(evals)
        # normalize by the sum of eigenvalues
        variance_explained = csum/np.sum(evals)
        return variance_explained

   # plot functions ====================================================================
    def plot_eigenvalues(self, evals):
        """
        Plots eigenvalues.
        Args:
            (numpy array of floats) : Vector of eigenvalues
        Returns:
            Nothing.
        """
        plt.figure()
        plt.plot(np.arange(1, len(evals) + 1), evals, 'o-k')
        plt.xlabel('Component')
        plt.ylabel('Eigenvalue')
        plt.title('Scree plot')

        
    def plot_variance_explained(self, variance_explained, variance_level):
        """
        Plots eigenvalues.
        Args:
            variance_explained (numpy array of floats) : Vector of variance explained
                                                        for each PC
            variance_level (float): vertical line at % variance explained
        Returns:
            Nothing.
        """
        plt.figure()
        plt.plot(np.arange(1, len(variance_explained) + 1), variance_explained, '--k', label='Variance Explained')
        # plot vertica line wher variance explained exceeds variance_level
        PC = np.argmax(variance_explained>variance_level)
        plt.vlines(PC, variance_explained.min(), 
                    variance_explained.max(), colors='r', label=f"{variance_level} % Variance Explained wit first {PC} components")
        # add label with variance_level and PC at that level
        plt.legend()
        plt.xlabel('Number of components')
        plt.ylabel('Variance explained')

    def plot_pca_scatter(self, scores, pc1, pc2, labels, print_labels=False, facecolor='r', edgecolor='r', fig=None, ax=None):
        """2d scatter plot with ability to specify colour and shape of point and plot trial number for each point 

        Args:
            score (float): values for features in new PC base
            pc1 (int): principal component vecotr for x axis
            pc2 (int): principal component vector for y axis   
            label (any): labels to plot for datapoints (must be same length as selected scores)
            print_label (bool, optional):  Defaults to False.
            facecolor (str, optional): . Defaults to 'r'.
            edgecolor (str, optional): if face and edge colour same = full point Defaults to 'r'.
            fig ([type], optional): optional pass fig if not will be created. Defaults to None.
            ax ([type], optional): [description]. Defaults to None.

        Returns:
            [type]: [description]
        """        
        if fig is None:
            fig, ax = plt.subplots()
        # get data
        xs = scores[:,pc1]
        ys = scores[:,pc2]
        # plot each trial
        ax.scatter(xs, ys, facecolors=facecolor, edgecolors=edgecolor)
        # add labels and title
        plt.xlabel(f"Principal component {pc1}")
        plt.ylabel(f"Principal component {pc2}")
        plt.title("Trials for two principal components")
        # add datapoints
        if print_labels:
            # zip joins x and y coordinates and palebls in pairs
            for x,y,label in zip(xs,ys,labels):
                # this method is called for each point
                plt.annotate(label, # this is the text
                            (x,y), # this is the point to label
                            textcoords="offset points", # how to position the text
                            xytext=(0,5), # distance from text to points (x,y)
                            size=5,
                            ha='center') # horizontal alignment can be left, right or center
        return fig, ax

    def plot_pca_scatter_animated(self, scores, pc1, pc2, fig=None, ax=None, line_col='grey', line_width=1, 
                         maker_shape='o', marker_col='red', marker_facecol='red', marker_size=4):  
        """animate 2d scatter plot

        Args:
            score (float): values for features in new PC base
            pc1 (int): principal component vecotr for x axis
            pc2 (int): principal component vector for y axis 
            fig ([type], optional): optional pass fig if not will be created. Defaults to None.
            ax ([type], optional): [description]. Defaults to None.
            line_col (str, optional): [description]. Defaults to 'grey'.
            line_width (int, optional): [description]. Defaults to 1.
            maker_shape (str, optional): [description]. Defaults to 'o'.
            marker_col (str, optional): [description]. Defaults to 'red'.
            marker_facecol (str, optional): [description]. Defaults to 'red'.
            marker_size (int, optional): [description]. Defaults to 4.

        Returns:
            fig (matplotlib subplot figure)
            ax (matplotlib subplot axis)
            anim (matplotlib animation): [description]
        """        
        # initialize firuge
        if fig is None:
            fig, ax = plt.subplots()
        # specify data
        xs = scores[:,pc1]
        ys = scores[:,pc2]
        # set axis max min
        ax.set_xlim([np.min(xs)-50, np.max(xs)+50])
        ax.set_ylim([np.min(ys)-50, np.max(ys)+50])
        # add labels and title
        ax.set_xlabel(f"Principal component {pc1}")
        ax.set_ylabel(f"Principal component {pc2}")
        ax.set_title("Trials for two principal components")
        # init plot
        graph, = ax.plot([] , [], zorder=1, #plot data
                        color=line_col, linewidth=line_width, #set line params
                        marker=maker_shape, markeredgecolor=marker_col, markerfacecolor=marker_facecol, markersize=marker_size) #set dots
        # define animation function
        def update(i, xs, ys, graph):
            graph.set_data(xs[:i], ys[:i])
            return graph
        # animation
        anim = animation.FuncAnimation(fig, update,  len(xs), fargs=[xs, ys, graph], blit=True, interval=80, repeat=False)
        return fig, ax, anim


# ===============================================================================================================================================


class eda():
    """[library to perfrom exploratory data analyis on spikes]
    """    
    def __init__(self, data, session, main_folder, params):
        """[initialize session analyse object]

        Args:
            data ([toubple]): [(spikes_df, clusters_df, trials_df)]
            session ([string]): [session folder]
            main_folder ([type]): [description]
            params ([dict]): [dictionary with all necessary infromation
                                params['sampling_rate] ([int]): [sampling rate for spikes]
                            ]
        """        
        self.folder = main_folder
        self.spikes_df, self.clusters_df, self.trials_df = data
        self.session = session
        # load all parameters
        if 'sampling_rate' in params:
            self.sampling_rate = params['sampling_rate']
        else:
            self.sampling_rate = 20000


 # Helper Functions EDA =================================================================================================
    # find spikes between
    def get_spikes_for_trial(self, array, start, stop):
        '''
        params: array = numpy array (N,1) with values to check against
                start, stop = value to find all values in array between
        return: valus in array between start and stop
        '''
        ar = array[np.logical_and(array >= start, array <= stop)]
        if ar.size > 0:
            ar = ar[:] - start
        return ar






 # Plotting ==========================================================================================================
    # event plot for all spikes
    def plt_spike_train(self, cluster, spikes, trials_df, params=dict()):
        """[generate spike event plot for given spikes and given trial start and end]

        Args:
            cluster ([int]): [selected neuron]
            spikes ([numpy array]): [spikes for neuron to plot]
            trials_df ([pandas data frame]): [format: index=trial, col1=start of trial, col2=stop of trial]
            params ([dict]): [optional, default = empty, params['brain_region' = brain region of cluster] ]

        Returns:
            [type]: [description]
        """        
        # initialize plot
        fig, ax = plt.subplots()
        # initialize list with spikes per trial
        spikes_trials = []
        # get spikes for each trial
        for row in trials_df.index:
            start = trials_df.iloc[row, 0]
            stop = trials_df.iloc[row, 1]
            spk = self.get_spikes_for_trial(spikes, start, stop)
            #if len(spk)>0:
            spikes_trials.append(spk)
        # plot spikes
        ax.eventplot(spikes_trials, color=".2")
        # set title and axis labels
        if 'brain_region' in params:
            ax.set_title(f"Spikes for Cluster {cluster}, Brain Region: {params['brain_region']}")
        ax.set_title(f"Spikes for Cluster {cluster}")
        ax.set_xlabel(f"Sampling Points [{self.sampling_rate/1000}kHz]")
        ax.set_ylabel('Trial')
        index = trials_df.index[0::10]
        ax.set_yticks(index - index[0])
        ax.set_yticklabels(index)
        return ax, fig

        # Tweak spacing to prevent clipping of ylabel
        fig.tight_layout()
        plt.show

    # plot spike trains araound event with histogram for spike time and trial
    def plt_spike_train_hist_bar(self, cluster, event, window, trials_df, spikes_ar, fig=None, ax=[None, None, None], title=None):
        """[summary]

        Args:
            cluster ([int]): [neuron to plot]
            event ([string]): [event name]
            window ([int]): [window to plot spikes: event_time-window < spikes < event_time+window]
            trials_df ([dataframe]): [event times to plot for, must be only column in dataframe]
            spikes_ar ([numpy array]): [array with all spikes of neuron to plot]
            fig ([plt.subfig figure], optional): [description]. Defaults to None.
            ax (plt.subfig axis, optional): [description]. Defaults to [None, None, None].
            title ([string], optional): [description]. Defaults to None.

        Returns:
            fig [plt.subfig figure]: [description]
            (ax1, ax2, ax3) [plt.subfig axis]: [description]

        """        
        # create fig, gird and axis ===============
        if any(i==None for i in ax) or fig==None:
            #create figure with shape
            fig = plt.figure(figsize=(6,5))
            # create gridspecs
            gs = fig.add_gridspec(2, 3,  hspace=0, wspace=0)
            # create axis for hist spike train
            ax1 = fig.add_subplot(gs[0, :2])
            ax2 = fig.add_subplot(gs[1, :2])
            ax2.get_shared_x_axes().join(ax1, ax2)
            # create axis for trial hist
            ax3 = fig.add_subplot(gs[0, 2])
            ax3.get_shared_y_axes().join(ax1, ax3)
        else:
            ax1, ax2, ax3 = ax
        
        # loop that iterats trough all trials
        y = 0
        # array to store spike count for each trial
        hist_tr = np.empty([0,])    
        # list to store spikes for time bin in for eventplot and histogram
        #spk_ar = np.empty((len(trials_df),1), dtype=object)
        spk_ls = []


        ##spike train plot ========================
        # main loop over each trial
        for row in trials_df.index:
            # derive spike times in range delta around event time for trial
            ar = spikes_ar[( ( spikes_ar >= (trials_df[row] - window) ) & ( spikes_ar <= (trials_df[row] + window) ) )]
            ar = ar - trials_df[row]
            # ad spike count to hist_tr for row
            hist_tr = np.append(hist_tr, ar.size)
            # add to histogram array
            spk_ls.append(ar.flatten().tolist())

        # plot eventplot
        ax1.eventplot(spk_ls, color=".2")
        ## draw red line at event
        ax1.axvline(x=0,ymin=0,ymax=1,c="red",linewidth=0.5)
        # spike train y lable
        ax1.set_ylabel('Trial')
        ## set y axis 1. plot
        # set ticks
        step = trials_df.index.size/5
        start = 0
        stop = trials_df.index.size+step/2
        ax1.set_yticks(np.arange(start, stop, step).astype(int))
        # set tick labels
        stop = trials_df.index.size
        label = trials_df.index.values[np.arange(start, stop, step).astype(int)]
        label = np.append(label, trials_df.index.values[-1])
        ax1.set_yticklabels(label)
        # set y limits 1. plot
        ax1.set_ylim([0, stop])
        ##labels
        # trun x labels inside
        ax1.tick_params(axis="x",direction="in")
        # turn of labels on shared x axis only ticks
        plt.setp(ax1.get_xticklabels(), visible=False)
        # write event
        ax1.set_title(event, color='red', fontsize=8)

        ## plot histogram spikes ===========================
        num_bins = 60
        # flatten list of sikes for histogram
        flattened = [val for sublist in spk_ls for val in sublist]
        # draw histogram
        ax2.hist(flattened, bins=num_bins, color="tab:blue")
        # draw red line at event
        ax2.axvline(x=0,ymin=0,ymax=1,c="red",linewidth=0.5)
        # naming y axis
        ax2.set_ylabel('Spike Count')
        # set x ticks
        step = window/4
        start = -window
        stop = window+(step/2)
        x_ticks = np.arange(start, stop, step)
        ax2.set_xticks(x_ticks)
        # set x ticks labels to seconds
        # set x limits
        ax2.set_xlim([-window, window])
        if window > 1000:
            window = window/1000
        step = window/4
        start = -window
        stop = window+(step/2)
        x_labels = np.arange(start, stop, step)
        ax2.set_xticklabels(x_labels)
        # set ticks top and bottom
        ax2.tick_params(axis='x', bottom=True, top=True)


        ## plot histogram trials =================================
        pos = np.arange(0, len(hist_tr))
        # invert axis
        ax3.invert_xaxis()
        # remove ticks
        ax3.set_yticks([])

        ## plot histogram
        ax3 = plt.barh(pos, hist_tr.reshape(hist_tr.size), height=1.0, color='lightgray')

        # name main title
        #ax.set_title('Spikes for Cluster 1')
        if title != None:
            event = title
        fig.suptitle(f"Spikes for Cluster: {cluster} at Event: {event}")
        plt.xlabel('Position [ms]')
        
        return fig, (ax1, ax2, ax3)



 # Report Generation ===================================================================================================



# ===============================================================================================================================================



class loader():
    """[class to load each session and cleanup data]

    Returns:
        [type]: [description]
    """    
    def __init__(self, main_folder, init_default=False, dt=1/1000, dT=2.5, T0=0.5):
        """[initialize object]

        Args:
            #main_folder ([string]): [filepath to all the sessions folders]
            init_default (bool, optional): [initialize first folder in parent folder]. Defaults to True.
            dt ([type], optional): [timewindow for spikes_ar]. Defaults to 1/1000.
            dT (float, optional): [description]. Defaults to 2.5.
            T0 (float, optional): [start time for spikes_ar]. Defaults to 0.5.
        """        
        self.dt = dt
        self.dT = dT
        self.T0 = T0
        self.regions, self.brain_groups = self.get_brain_region()
        self.folder=main_folder
        self.subfolders, self.all_sessions = self.get_available_session()
        # load first session
        if init_default:
            self.default_session = self.load_session(self.subfolders[0])
    
    #  find all available sessions
    def get_available_session(self):
        subfolders = [ f.path for f in os.scandir(self.folder) if f.is_dir() ]
        sessions = [os.path.basename(folder_) for folder_ in subfolders]
        return subfolders, sessions

    # load session from given sesion folder
    def load_session(self, folder, fast=False, update=False):
        """[load important information for each given session]

        Args:
            folder ([string]): [path to folder with session files to load]
            fast ([bool]): [true: complete dictionary isloaded, false: just trials_df, spikes_df, cluster_df, spikes_ar]
            update ([boo]): [true: trials_df, spikes_df, cluster_df, spikes_ar files are updated]

        Returns:
           session [dict]: [dictionary with keys:
                    folder: folder of session
                    spikes_df: dataframe with all spikes and cluster belonging to
                    clusters_df: infromation about neurons with spikes
                    trials_df: infromation about trials, times, and wheel movement
                    clusters = good_cells
                    brain_area = brain_regions
                    spikes_ar: binned spikes for each neuron and each trial
                    wheel: wheel movement per trial
                    pupil: pupil diameter per time bin
                    response = response
                    contrast_right: vis_right
                    contrast_left: vis_left
                    response_time: rsp
                    feedback_time: feedback
                    feedback_type: feedback_type  
                    gocue: gocue
                    mouse_name
                    date_exp
                    trough_to_peak
                    waveform_w
                    waveform_u
                    bin_size
                    stim_onset
                    spikes_ar_passive: binned spikes for each neuron and each passive trial
                    wheel_passive: wheel movement per passive trial
                    pupil_passive: 
                    contrast_right_passive: 
                    contrast_left_passive: ]
        """        
        # check if fast is selected

        files = ['trials_df.pd', 'spikes_df.pd', 'clusters_df.pd']#, 'spikes_ar.npy']
        files_exist = [ path.exists( os.path.join(folder, fi) ) for fi in files ]
        if fast and all(files_exist):
            session = dict()
            #session['trials_df'] = pd.read_csv(os.path.join(folder, 'trials_df.csv') )
            session['trials_df'] = pd.read_pickle(os.path.join(folder, 'trials_df.pd'), compression='gzip' )
            #session['spikes_df'] = pd.read_csv(os.path.join(folder, 'spikes_df.csv') )
            session['spikes_df'] = pd.read_pickle(os.path.join(folder, 'spikes_df.pd'), compression='gzip' )
            #session['clusters_df'] = pd.read_csv(os.path.join(folder, 'clusters_df.csv') )
            session['clusters_df'] = pd.read_pickle(os.path.join(folder, 'clusters_df.pd'), compression='gzip' )
            #session['spikes_ar'] = np.load(os.path.join(folder, 'spikes_ar.npy') )
            #session['spikes_ar'] = sparse.load_npz(os.path.join(folder, 'spikes_ar.npy') ).toarray()



        else:
            # load session files into dictionary ===========================================

            ## load session files ===========================================
            #from os import listdir
            #from os.path import isfile, join
            #files = [f for f in listdir(folder) if isfile(join(folder, f))]
            #files = [f for f in files if f[:2]!='._'] #Samuel added this to deal with weird bug
            #names = ['_'.join(f.split('.')[:-1]) for f in files]
            #session = dict()
            #for (file_, name_) in zip(files, names):
            #    if file_.split('.')[-1] == 'npy':
            #        session[name_] = np.load(join(folder,file_))
            #    if file_.split('.')[-1] == 'tsv':
            #        session[name_] = pd.read_table(join(folder,file_))

            # Load Pachitariu Session Data ===========================================================================
            # good cells and brain regions
            good_cells, brain_region, br, phy_label = self.get_good_cells(folder)
            # get all spikes
            spk_spikes, spk_clusters = self.get_all_spikes(folder)
            # event types
            response, vis_right, vis_left, feedback_type, included_tr, rep_nrs = self.get_event_types(folder)
            # event timing
            response_times, visual_times, gocue_times, feedback_times, interval_times, rsp, feedback, gocue, interval = self.get_event_times(folder)   
            # get passive trials
            vis_times_p, vis_right_p, vis_left_p, gocue_p = self.get_passive(folder)
            visual_times = np.vstack((visual_times, vis_times_p))
            vis_right = np.hstack((vis_right, vis_right_p))
            vis_left  = np.hstack((vis_left, vis_left_p))
            # get spikes and clusters of spikes
            spikes, sclust    = self.get_spikes(folder)
            # wheel traces
            wheel, wheel_times = self.get_wheel(folder)
            # load the pupil
            pup, xy, pup_times = self.get_pup(folder)
            # load the LFP
            #L, ba_lfp = self.get_LFP(folder, br, visual_times-T0, dT, dt, T0)
            
            # wheel trials
            W = self.wpsth(wheel, wheel_times,   visual_times-self.T0, self.dT, self.dt)
            # pupil loader
            P = self.ppsth(pup, pup_times,   visual_times-self.T0, self.dT, self.dt)
            # add spike waveform information
            twav, w, u = self.get_waves(folder)
            
            
            # put all the variables into dictionary
            session = dict()
            # _p mens for passif trials
            # number of active trials
            ntrials = len(response)
            session['folder'] = folder
            session['clusters'] = np.arange(len(good_cells))[good_cells]
            session['brain_area'] = brain_region[good_cells]
            session['wheel'] = W[np.newaxis, :ntrials, :]
            session['pupil'] = P[:, :ntrials, :]
            session['response'] = response
            session['contrast_right'] = vis_right[:ntrials]
            session['contrast_left'] = vis_left[:ntrials]
            session['response_time'] = rsp
            session['feedback_time'] = feedback
            session['feedback_type'] = feedback_type  
            session['gocue'] = gocue
            #session['mouse_name'] = folder.split('\\')[1].split('_')[0]
            #session['date_exp'] = folder.split('\\')[1].split('_')[1]
            session['trough_to_peak'] = twav[good_cells].flatten()
            session['waveform_w'] = w[good_cells].astype('float32')
            session['waveform_u'] = u[good_cells].astype('float32')
            session['bin_size'] = self.dt
            session['stim_onset'] = self.T0
            session['wheel_passive'] = W[np.newaxis, ntrials:, :]
            session['pupil_passive'] = P[:, ntrials:, :]
            #session['lfp_passive'] = L[:, ntrials:, :]
            session['contrast_right_passive'] = vis_right[ntrials:]
            session['contrast_left_passive'] = vis_left[ntrials:]
            

            # pars probe infos ============================================================================
                # # load channel brain location infos
                # brain = pd.DataFrame(session['channels_brainLocation'])
                # # load channel probes
                # site = pd.DataFrame(session['channels_sitePositions'], columns=['channel 0', 'channel 1'])
                # # merge with channles_df
                # channels_df = pd.merge(brain, site, how='inner', left_index=True, right_index=True)
                # # load probe, row and site
                # meta = pd.DataFrame({'probe':session['channels_probe'][:,0],
                #                             'raw row':session['channels_rawRow'][:,0],
                #                             'channels_site':session['channels_site'][:,0] })
                # # merge metha with channel_df
                # channels_df = pd.merge(channels_df, meta, how='inner', left_index=True, right_index=True)
                # # add channels_df to session dictionary
                # session['channels_df']=channels_df

            # create spikes dataframe spikes_df ============================================================================
            # create spike_df tataframe, with each spike time and the cluster it belongs to
            spikes_df = pd.DataFrame( { 'cluster':spk_clusters[:,0], 'spike_times': spk_spikes[:,0] }) 
            # add spikes to session dictionary
            session['spikes_df']=spikes_df

            # create clusters/neurons dataframe clusters_df ============================================================================
            #clusters = np.unique(spikes_df['cluster'])
            # create number of spikes, phy2 manual cluster, 
            clusters = np.unique(spk_clusters)
            clusters_df = pd.DataFrame({'label':phy_label}, index=clusters )
            clusters_df['label'] = clusters_df['label'].apply( lambda label: 'good' if label==2 else ('mua' if label==1 else 'bad') )
            # drop rows with bad cells
            #clusters_df.drop( clusters_df[(clusters_df['label']=='bad')].index,axis=0,inplace=True)
            # create spikes colum with spiketimes

            spk = pd.DataFrame( {'spikes':np.zeros(len(clusters), dtype=object)}, index=clusters )
            # only select good clusters
            for group, frame in spikes_df.groupby('cluster'):
                spk['spikes'][group] = frame['spike_times'].values
            #merge spike column with clusters_df
            clusters_df = pd.merge(clusters_df, spk, how='right', left_index=True, right_index=True)
            # set index name
            clusters_df.index.name='cluster'
            # number of spikes per cluster
            clusters_df['total spikes'] = clusters_df['spikes'].apply(lambda row: len(row) )
            # add recording position
            clusters_df['recording area'] = brain_region

            session['clusters_df'] = clusters_df


            # create active trials dataframe activ_trials_df ============================================================================
            # create trials dataframe
            trials_df = pd.DataFrame({'included':included_tr,
                        'repetition number':rep_nrs,
                        'start time':interval_times[:,0],
                        'stim time':visual_times[:ntrials, :].flatten(),
                        'go cue':gocue_times.flatten(),
                        'response time':response_times.flatten(),
                        'feedback time':feedback_times.flatten(),
                        'end time':interval_times[:,1],
                        'stim contrast left':vis_left[:ntrials].flatten(),
                        'stim contrast right':vis_right[:ntrials].flatten(),
                        'response choice':response,
                        'feedback type':feedback_type,
                        })
            trials_df = trials_df.astype(dtype= {"repetition number":"int8", 
                                                'stim contrast left':'int8', 
                                                'stim contrast right':'int8',
                                                'response choice': 'int8',
                                                'feedback type':'int8'
                                                })
            # add wheelmovement to trials dv ===============
            #wheel = W[np.newaxis, :, :]
            whl = pd.DataFrame( {'wheel movement':np.zeros(ntrials)}, dtype=object) 
            for row in range(W.shape[0]):
                whl['wheel movement'][row] = W[row,:]

            #merge trials with wheel
            trials_df = pd.merge(trials_df, whl, how='right', left_index=True, right_index=True)

            # add trials df to session
            session['trials_df'] = trials_df

        # write files if update or file does not exist
        if update or any(files_exist):
            #session['trials_df'].to_csv(os.path.join(folder, 'trials_df.csv') )
            session['trials_df'].to_pickle(os.path.join(folder, 'trials_df.pd'), compression='gzip' )    
            #session['spikes_df'].to_csv(os.path.join(folder, 'spikes_df.csv') )
            session['spikes_df'].to_pickle(os.path.join(folder, 'spikes_df.pd'), compression='gzip' )
            #session['clusters_df'].to_csv(os.path.join(folder, 'clusters_df.csv') )
            session['clusters_df'].to_pickle(os.path.join(folder, 'clusters_df.pd'), compression='gzip' )
            # spikes are is too big - dont load it by default
            #np.save( os.path.join(folder, 'spikes_ar.npy'), session['spikes_ar'], allow_pickle=True )
            #sparse.save_npz(os.path.join(folder, 'spikes_ar.npy'), sparse.csr_matrix(session['spikes_ar']) )
        

        return session
    
    # load binned spikes for all trials and all sessions
    def binned_spikes(self, folder, TO=None, dT=None, dt=None):
        """[load spikes for all good neurons an all trials binned to 250 bins per trial]

        Args:
            folder ([string]): [folder of session to load, default =]
            T0 ([float]): [start time for each trial bin default T0=0.5]
            dT ([float]): [bin width, default dT=2.5]
            dt ([float]): [bin steps default  dt=1/1000]

        Returns:
            spikes_ar ([numpy array]): [spikes of active trials (neuron, trial, bin)]
            spikes_ar ([numpy array]): [spikes of passive trials (neuron, trial_passiv, bin)]
        """        
        # ititialize default values:
        if T0 is None:
            TO=self.T0
        if dT is None:
            dT=self.dT
        if dt is None:
            dt=self.dt
        # event times
        response_times, visual_times, _, _, _, _, _, _,  = self.get_event_times(folder)   
        # get spikes and clusters of spikes
        spikes, sclust = self.get_spikes(folder)
        # trials loader
        ntrials = len(response_times)
        S  = self.psth(spikes, sclust,   visual_times-self.T0, self.dT, self.dt)
        S  = S[good_cells].astype('int8') 
        spikes_ar=S[:, :ntrials, :]
        spikes_ar_passive = S[:, ntrials:, :]
        return spikes_ar, spikes_ar_passive

    # save wheel movement per trial to numpy array in session folder
    def save_wheel_to_npy(self, session):
        """[save the wheel movement of active and passive trials to npy file]

        Args:
            session ([dict]): [session to save wheel movement from]
        """        
        folder = session['folder']
        # save wheel movement of active trials
        fname = os.path.join(folder, "wheel_per_trial.npy")
        numpy.save(fname, session['wheel'], allow_pickle=True)
        # save wheel movement of passive trials
        fname = os.path.join(folder, "wheel_per_trial_p.npy")
        numpy.save(fname, session['wheel_passive'], allow_pickle=True)
        

    # get spikes for given array within start stop sequence
    def get_spikes_for_trial(self, array, start, stop): 
        '''
        params: array = numpy array (N,1) with values to check against
                start, stop = value to find all values in array between
        return: valus in array between start and stop
        '''
        ar = array[np.logical_and(array >= start, array <= stop)]
        if ar.size > 0:
            ar = ar[:] - ar[0]
        return ar

 # Helper Functions to Load Data ============================================================================
    def get_good_cells(self, folder):
        # location in brain of each neuron
        brain_loc = os.path.join(folder, "channels.brainLocation.tsv")
        phy_label = np.load(os.path.join(folder, "clusters._phy_annotation.npy")).flatten()
        phy_label_good = (phy_label >= 2)
        clust_channel = np.load(os.path.join(folder, "clusters.peakChannel.npy")).astype(int) - 1
        br = []
        with open(brain_loc, 'r') as tsv:
            tsvin = csv.reader(tsv, delimiter="\t")
            k=0
            for row in tsvin:
                if k>0:
                    br.append(row[-1])
                k+=1
        br = np.array(br)
        good_cells = np.logical_and(phy_label_good, clust_channel.flatten()<len(br))
        brain_region = br[clust_channel[:,0]]


        return good_cells, brain_region, br, phy_label

    def get_all_spikes(self, folder):
        fname = os.path.join(folder, "spikes.times.npy")
        spikes = np.load(fname)
        fname = os.path.join(folder, "spikes.clusters.npy")
        clusters = np.load(fname)

        return spikes, clusters

    def get_waves(self, folder):
        fname = os.path.join(folder, "clusters.waveformDuration.npy")
        twav = np.load(fname)

        fname = os.path.join(folder, "clusters.templateWaveforms.npy")
        W = np.load(fname)

        fname = os.path.join(folder, "clusters.templateWaveformChans.npy")
        ichan = np.load(fname).astype('int32')

        u = np.zeros((W.shape[0], 3, 384))
        w = np.zeros((W.shape[0], 82, 3))

        for j in range(W.shape[0]):
            wU  = TruncatedSVD(n_components = 3).fit(W[j]).components_
            wW = W[j] @ wU.T
            u[j][:, ichan[j]%384] = wU
            w[j] = wW

        return twav, w, u


    def get_probe(self, br, folder):
        prb_name = os.path.join(folder, "probes.rawFilename.tsv")
        prb = []
        with open(prb_name, 'r') as tsv:
            tsvin = csv.reader(tsv, delimiter="\t")
            for row in tsvin:
                prb.append(row[-1])
            prb = prb[1:]
        for ip in range(len(prb)):
            pparts = prb[ip].split('_')
            prb[ip] = '%s_%s_%s_%s'%(pparts[0], pparts[1], pparts[2], pparts[3])

        brow = []
        blfp = []
        for iprobe in range(len(prb)):
            ch_prb = np.load(os.path.join(folder, "channels.probe.npy")).astype(int)
            raw_row = np.load(os.path.join(folder, "channels.rawRow.npy")).astype(int)
            ich = (ch_prb.flatten()==iprobe).nonzero()[0]
            bunq = np.unique(br[ich])
            bunq = bunq[bunq!='root']
            nareas = len(bunq)
            brow.append([])
            for j in range(nareas):
                bid = br[ich]==bunq[j]
                brow[-1].append(raw_row[ich[bid], 0])
            blfp.append(bunq)
        return prb, blfp, brow


    def get_LFP(self, br, etime, dT, dt, T0, folder):
        prb, blfp, brow = get_probe(folder, br)
        bsize = 100000
        nbytesread = 385 * bsize * 2

        L = []
        BA_LFP = []
        for ip in range(len(prb)):
            BA_LFP.extend(blfp[ip])

            # root = self.folder
            # ''Z:/3 Projekte/Neuromatch Summer School/Projekt/steinmetz_dataset\\Cori_2016-12-14\\Cori_2016-12-14_M2_g0_t0.imec.lf.bin'
            # fname_lfp = '%s_t0.imec.lf.bin'%(prb[ip])

            # LFP = []
            # with open(os.path.join(root, fname_lfp), 'rb') as lfp_file:
            #     while True:
            #         buff = lfp_file.read(nbytesread)
            #         data = np.frombuffer(buff, dtype=np.int16, offset=0)
            #         if data.size==0:
            #             break
            #         data = np.reshape(data, (-1, 385))

            #         nareas = len(brow[ip])
            #         lfp = np.zeros((data.shape[0], nareas))
            #         for j in range(nareas):
            #             lfp[:,j] = data[:, brow[ip][j]].mean(-1)
            #         LFP.extend(lfp)
            # LFP = np.array(LFP)
            fname_lfp_times = '%s_t0.imec.lf.timestamps.npy'%(prb[ip])
            lfp_times = np.load(os.path.join(folder, fname_lfp_times))
            L.extend(ppsth(LFP, lfp_times,  etime, dT, dt))

        L = np.array(L)
        L = L - np.expand_dims(np.mean(L[:,:,:int(T0//dt)], axis=-1), axis=-1)

        return L, BA_LFP

    def get_passive(self, folder):
        vis_right_p = np.load(os.path.join(folder, "passiveVisual.contrastRight.npy")).flatten()
        vis_left_p = np.load(os.path.join(folder, "passiveVisual.contrastLeft.npy")).flatten()
        vis_times_p = np.load(os.path.join(folder,   "passiveVisual.times.npy"))
        gocue_p = np.load(os.path.join(folder, "passiveBeeps.times.npy"))

        return vis_times_p, vis_right_p, vis_left_p, gocue_p


    def get_event_types(self, folder):
        response = np.load(os.path.join(folder, "trials.response_choice.npy")).flatten()
        vis_right = np.load(os.path.join(folder, "trials.visualStim_contrastRight.npy")).flatten()
        vis_left = np.load(os.path.join(folder, "trials.visualStim_contrastLeft.npy")).flatten()
        feedback_type = np.load(os.path.join(folder, "trials.feedbackType.npy")).flatten()
        included_tr= np.load(os.path.join(folder, "trials.included.npy")).flatten()
        rep_nr= np.load(os.path.join(folder, "trials.repNum.npy")).flatten()

        return response, vis_right, vis_left, feedback_type, included_tr, rep_nr

    def get_event_times(self, folder):
        response_times = np.load(os.path.join(folder, "trials.response_times.npy"))
        visual_times = np.load(os.path.join(folder,   "trials.visualStim_times.npy"))
        gocue_times = np.load(os.path.join(folder,   "trials.goCue_times.npy"))
        feedback_times = np.load(os.path.join(folder,   "trials.feedback_times.npy"))
        interval_times = np.load(os.path.join(folder, "trials.intervals.npy"))

        rsp = response_times - visual_times
        feedback = feedback_times - visual_times
        gocue = gocue_times - visual_times
        interval = interval_times - visual_times

        return response_times, visual_times, gocue_times, feedback_times, interval_times, rsp, feedback, gocue, interval

    def get_wheel(self, folder):
        wheel = np.load(os.path.join(folder, "wheel.position.npy")).flatten()
        wheel_times = np.load(os.path.join(folder,   "wheel.timestamps.npy"))
        return wheel, wheel_times

    def get_pup(self, folder):
        pup = np.load(os.path.join(folder, "eye.area.npy"))
        pup_times = np.load(os.path.join(folder,  "eye.timestamps.npy"))
        xy = np.load(os.path.join(folder, "eye.xyPos.npy"))

        return pup, xy, pup_times

    def get_spikes(self, folder):
        stimes = np.load(os.path.join(folder, "spikes.times.npy")).flatten()
        sclust = np.load(os.path.join(folder, "spikes.clusters.npy")).flatten()
        return stimes, sclust

    def first_spikes(self, stimes, t0):
        tlow = 0
        thigh = len(stimes)

        while thigh>tlow+1:
            thalf = (thigh + tlow)//2
            sthalf = stimes[thalf]
            if t0 >= sthalf:
                tlow = thalf
            else:
                thigh = thalf
        return thigh

    def wpsth(self, wheel, wheel_times, etime, dT, dt):
        ntrials = len(etime)
        NT = int(dT/dt)
        f = interp1d(wheel_times[:,1], wheel_times[:,0], fill_value='extrapolate')
        S  = np.zeros((ntrials, NT))
        for j in range(ntrials):
            tsamp = f(np.arange(etime[j], etime[j]+dT+1e-5, dt)).astype('int32')
            S[j,:] = wheel[tsamp[1:]] - wheel[tsamp[:-1]]
        return S

    def ppsth(self, pup, pup_times, etime, dT, dt):
        nk = pup.shape[-1]
        ntrials = len(etime)
        NT = int(dT/dt)
        f = interp1d(pup_times[:,1], pup_times[:,0], fill_value='extrapolate')
        S  = np.zeros((nk, ntrials, NT))
        for k in range(nk):
            for j in range(ntrials):
                tsamp = f(np.arange(etime[j], etime[j]+dT-1e-5, dt) + dt/2).astype('int32')
                S[k, j,:] = pup[tsamp, k]
        return S

    def psth(self, stimes, sclust, etime, dT, dt):
        NN = np.max(sclust)+1
        NT = int(dT/dt)
        ntrials = len(etime)

        S  = np.zeros((NN, ntrials, NT))
        for j in range(ntrials):
            k1   = self.first_spikes(stimes, etime[j])
            k2   = self.first_spikes(stimes, etime[j]+dT)
            st   = stimes[k1:k2] - etime[j]
            clu  = sclust[k1:k2]
            S[:,j,:] = csr_matrix((np.ones(k2-k1), (clu, np.int32(st/dt))), shape=(NN,NT)).todense()

        return S

    def get_brain_region(self):
        regions = ["vis ctx", "thal", "hipp", "other ctx", "midbrain",  "basal ganglia", "subplate"]
        brain_groups = [["VISa", "VISam", "VISl", "VISp", "VISpm", "VISrl"], # visual cortex
                        ["CL", "LD", "LGd", "LH", "LP", "MD", "MG", "PO", "POL", "PT", "RT", "SPF", "TH", "VAL", "VPL", "VPM"], # thalamus
                        ["CA", "CA1", "CA2", "CA3", "DG", "SUB", "POST"], # hippocampal
                        ["ACA", "AUD", "COA", "DP", "ILA", "MOp", "MOs", "OLF", "ORB", "ORBm", "PIR", "PL", "SSp", "SSs", "RSP"," TT"], # non-visual cortex
                        ["APN", "IC", "MB", "MRN", "NB", "PAG", "RN", "SCs", "SCm", "SCig", "SCsg", "ZI"], # midbrain
                        ["ACB", "CP", "GPe", "LS", "LSc", "LSr", "MS", "OT", "SNr", "SI"], # basal ganglia 
                        ["BLA", "BMA", "EP", "EPd", "MEA"] # cortical subplate
                    ]
        return regions, brain_groups


