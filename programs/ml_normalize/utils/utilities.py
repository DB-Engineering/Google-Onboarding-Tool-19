import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.preprocessing import LabelEncoder

def plot_graphs(history_1, string):
    plt.plot(history_1.history[string])
    plt.plot(history_1.history['val_'+string])
    plt.xlabel("Epochs")
    plt.ylabel(string)
    plt.legend([string, 'val_'+string])
    plt.show()

def remove_enumeration(x):
    return re.sub('_[0-9]+$', '', x).rstrip('_') if isinstance(x, str)==True else np.nan

def remove_symbols(x):
    regex = r"[\s\w\d-_]"
    return re.sub(' +', ' ', ''.join(re.findall(regex, x, re.MULTILINE)))

def lowercase(x):
    return x.lower()

def preprocess_inputs(inputs: pd.DataFrame, feature_cols: list = None) -> pd.Series:
    NON_ASCII_PATTERN = r"[^\x20-\x7E]"
    SYMBOLS_PATTERN = r"[#'&:/()?,+\\]"

    if not feature_cols:
        feature_cols = ['controlProgram', 'name', 'objectName', 'type']

    missing_cols = [_ for _ in feature_cols if _ not in inputs.columns]
    
    if len(missing_cols) > 0:
        raise KeyError(f"Missing required columns: {' ,'.join(missing_cols)}")

    inputs = inputs[feature_cols].copy()
    inputs.fillna("", inplace=True)

    inputs.loc[:, 'inputs'] = inputs[feature_cols].apply(lambda x: " ".join(x.astype(str)), axis=1)
    inputs.loc[:, 'inputs'] = inputs.inputs.apply(lambda x: re.sub(SYMBOLS_PATTERN, "", x))
    inputs.loc[:, 'inputs'] = inputs.inputs.apply(lambda x: re.sub(NON_ASCII_PATTERN, "", x)).str.strip()

    return inputs['inputs']

def encode_sequences(sequences: pd.Series, tokenizer, max_seq_length=180): # sequence length=80 was used in training
    """
    Turns a string into a sequence of indices using a pretrained tokenizer.
    Args:
    sequences: pandas Series with input text
    tokenizer: text tokenizer instance (tensorflow.keras.preprocessing.text.Tokenizer) from .pickle
    top_n: top n labels
    Returns: a dictionary: predcited label with predicted probability, and top_n predicted labels ordered by probability in ascending order
    """
    tonekized_sequences = tokenizer.texts_to_sequences(sequences)
    padded_sequences = pad_sequences(tonekized_sequences,
                        maxlen=max_seq_length,
                        padding='post',
                        truncating='post')
    return padded_sequences

def encode_labels(labels: pd.Series, label_encoder):
    """
    Args:
    labels: pandas Series with input text
    label_encoder: label encoder instance (sklearn.preprocessing.LabelEncoder) from .pickle
    Returns: a dictionary: predcited label with predicted probability, and top_n predicted labels ordered by probability in ascending order
    """
    NUMBER_OF_CLASSES = len(label_encoder.classes_)
    encoded_labels = np.array(label_encoder.transform(labels))
    encoded_labels_one_hot = tf.one_hot(encoded_labels, depth=NUMBER_OF_CLASSES)
    return encoded_labels_one_hot


def decode_sequence(input_sequence, tokenizer):
    text = ''.join([tokenizer.index_word[token] for token in input_sequence if token in tokenizer.index_word])
    
    return text

def decode_binary(model_outputs, encoder):
    class_probabilities = tf.reduce_max(model_outputs, axis=1)
    class_probabilities = tf.round(class_probabilities * 100) / 100
    class_indices = tf.argmax(model_outputs, axis=1)
    class_labels = encoder.inverse_transform(class_indices)
    return class_labels, class_probabilities

def decode_sparse_categorical(model_outputs, encoder):
    class_probabilities, class_indices = tf.math.top_k(model_outputs, k=3)
    class_labels = np.array([encoder.inverse_transform(row) for row in class_indices])

    pred_label = []
    pred_proba = []
    top_3 = []

    for x, y in zip(class_labels, class_probabilities):
        pred_label.append(x[0])
        pred_proba.append(round(float(y[0]), 2))
        temp = {}
        for ix, iy in zip(x[1:], y[1:]):
            if iy > 0.1:
                temp[ix] = round(float(iy), 2)
            else: 
                continue
        if len(temp.keys()) > 1:
            top_3.append(json.dumps(temp))
        else: top_3.append(np.nan)
    return pred_label, pred_proba, top_3

def decode_multiclass_binary(model_outputs, encoder):
    label_map = encoder.classes_
    def decode(class_vector):
        if len(class_vector) > 0:
            return ','.join([label_map[i] for i, prob in enumerate(class_vector.tolist()) if prob > 0.7])
        else: return np.nan
    labels = [decode(o) for o in model_outputs]
    return labels