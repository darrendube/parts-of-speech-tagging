import numpy as np
np.seterr(divide="ignore") # TODO: check if this is even necessary


# XXX: NOTE that this case (parts-of-speech tagging) is a supervised problem, 
# unlike the signature assignmetn in CS315 which was unsurpervied. in POS tagging,
# we are given the tags, so we can speed up training by simply counting transitions and
# estimating emission probabilities from the data. We can then load this information
# through some function like load(). So the main point of this class is to find the most
# likely state sequence for an unknown, test sequence, using viterbi
#
# XXX: in the load phase, remember to smooth after counting - in real data some 
# state transitions or word emission smay never appear in training, resulting in 
# a zero count, which makes porbabilities zero and thus certain paths impossible
# (even though they may be possible in real life). Avoid this by adding a small value 
# k to counts before normlisation 
#

class DiscreteRV:
    def __init__(self, tokens:np.ndarray, probabilities:np.ndarray):
        assert tokens.shape[0] == probabilities.shape[0], "Mismatch of lengths"
        print(probabilities)
        assert abs(sum(probabilities) - 1.0) < 1e-7, "Probabilities \
         do not add up to 1"
        self.tokens = tokens
        self.probabilities = probabilities
        self._dict = dict(zip(self.tokens, self.probabilities))

    def pmf(self, token):
        return self._dict.get(token, 0.0)

    def sample(self, n=1):
        return np.random.choice(self.tokens, size=n, p=self.probabilities)


class POSTagger:
    '''
    Class for classifying words in a text into their corresponding parts of speech.
    This is based on the Hidden Markov Model, where the hidden states are the
    parts of speech, and the observed variables are the words. 

    Usage:
    1. Initialise the class
    2. Either use `load()` to load a transition matrix and list of emission
    distributions, or train the model by passing training data to `fit()`
    3. Use `get_tags()` to tag a given text with its parts of speech (uses Viterbi
    decoding)
    4. Use `sample` to generate sample texts/sentences. NOTE: the sentences generated 
    are likely to be nonsensical as this clas doesn't model syntax, semantics, or context
    '''
    
    def fit(self, signals:list, tags:list):
        '''
        Train the POS Tagger using the training data provided in `signal` and 
        `tags`.

        Parameters
        ----------
        signals : str ndarray
            An array of training data, consisting of several different training
            sequences. Columns correspond to individual sequences

        tags : str ndarray
            An array of tags corresponding to each token in `signal`
        '''
        # TODO: count tag transitions and estimate state emission probabilities
        # from training data
        self._unique_tags = np.unique(np.concatenate(tags))
        self.A = self._estimate_trans_matrix(tags)
        self.state_dists = self._estimate_state_dists(signals, tags)
        

    def load_hmm(self, transition_matrix, state_dists):
        self.A = transition_matrix
        self.state_dists = state_dists

    def get_tags(self, signal:np.ndarray):
        # TODO: store tags in an array then simply work with ints
        np.seterr(invalid="ignore") # XXX: check if this is even necessary
        N = len(self.state_dists)
        T = signal.shape[0]
        
        Delt = np.zeros((N, T))
        Backp = np.zeros((N, T), dtype=int)

        # initialisation
        for j in range(N):
            Delt[j,0] = np.log(self.A[-1,j]) + self.state_dists[j].pmf(signal[0])
            Backp[j,0] = -1

        # recursion
        for t in range(1,T):
            for j in range(N):
                vals = []
                for i in range(N):
                    vals += [Delt[i,t-1] + np.log(self.A[i,j])]
                Delt[j, t] = self.state_dists[j].pmf(signal[t]) + np.max(vals)
                Backp[j, t] = int(np.argmax(vals))

        # termination
        vals = []
        for j in range(N):
            vals += [np.log(self.A[j, N]) + Delt[j,T-1]]
        b_T = np.argmax(vals)

        # get optimal state sequence
        seq = [b_T]
        t = T - 1
        curr = b_T
        while True:
            if Backp[int(curr), t] == -1:
                break
            seq += [int(Backp[int(curr), t])]
            curr = seq[-1]
            t -= 1

        return self._int_to_tag(np.array(seq)[::-1])

    def _estimate_trans_matrix(self, tags):
        N = self._unique_tags.shape[0]
        k = 1 # k value for smoothing
        state_seqs = [self._tag_to_int(tag_seq) for tag_seq in tags]
        transition_counts = np.zeros((N+1, N+1))
        # pad each state sequence with initial and terminal state
        for i in range(len(state_seqs)):
            state_seqs[i] = np.insert(state_seqs[i], 0, -1)
            state_seqs[i] = np.append(state_seqs[i], N)

        for seq in state_seqs:
            for i in range(seq.shape[0] - 1):
                transition_counts[seq[i], seq[i+1]] += 1
        transition_counts += k # add smoothing k

        return transition_counts / transition_counts.sum(axis=1, keepdims=True)

    def _estimate_state_dists(self, signals, tags):
        signals_flat = np.concatenate(signals)
        tags_flat = np.concatenate(tags)
        grouped_vals = {}
        state_dists = []
        print(self._unique_tags)
        for tag in self._unique_tags:
            grouped_vals[tag] = signals_flat[np.where(tags_flat == tag)[0]]
        for tag in self._unique_tags:
            unique_tokens, counts = np.unique(grouped_vals[tag], return_counts=True)
            probs = counts / counts.sum()
            state_dists += [DiscreteRV(unique_tokens, probs)]
        return state_dists

    def _int_to_tag(self, val):
        return self._unique_tags[val]

    def _tag_to_int(self, tag):
        to_index = np.vectorize(lambda x: np.where(self._unique_tags == x)[0][0])
        return to_index(tag)

    def sample(self):
        samples = []
        states = []
        curr_state = -1
        while True:
            state_trans_probs = self.A[curr_state]
            # sample next state based on current transition probabilities
            curr_state = np.random.choice(len(self._unique_tags) + 1, p=state_trans_probs)
            if curr_state == len(self.state_dists):
                states = np.array(states)
                return np.array(samples), self._int_to_tag(states)
            states += [curr_state]
            samples += [self.state_dists[curr_state].sample()]
        return samples, states

