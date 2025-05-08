import loadsheet.loadsheet as load

import pandas as pd
import numpy as np
import pickle
import json
import tensorflow as tf
import os
import re
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class MLHandler:
    def __init__(self):
        self.load_models()
        self.load_tokenizers()\

    def load_models(self):
        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "keras_models",
                "predict_required_conv1d2x_4fc_reg05.keras"
            )
            self.required_model = tf.keras.models.load_model(path)
        except Exception as e:
            print(f"[ERROR]: Could not load 'required' model: {e}")

        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "keras_models",
                "predict_generalType_conv1d2x_4fc_reg05.keras"
            )
            self.generalType_model = tf.keras.models.load_model(path)
        except Exception as e:
            print(f"[ERROR]: Could not load 'generalType' model: {e}")

        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "keras_models",
                "predict_standardfieldname_conv1d_6fc_reg05.keras"
            )
            self.standardfieldname_model = tf.keras.models.load_model(path)
        except Exception as e:
            print(f"[ERROR]: Could not load 'standardFieldName' model: {e}")

        self.models_loaded = True
        print("[INFO]\tModels loaded successfully.")

    def load_tokenizers(self):
        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "tokenizers",
                "char_tokenizer.pickle"
            )
            with open(path, 'rb') as handle:
                self.tokenizer = pickle.load(handle)
        except Exception as e:
            print(f"[ERROR]: Could not load character tokenizer: {e}")

        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "tokenizers",
                "binarizer_generalType.pickle"
            )
            with open(path, 'rb') as handle:
                self.binarizer_generalType = pickle.load(handle)
        except Exception as e:
            print(f"[ERROR]: Could not load generalType binarizer: {e}")

        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "tokenizers",
                "label_encoder_standardFieldName.pickle"
            )
            with open(path, 'rb') as handle:
                self.label_encoder_standardFieldName = pickle.load(handle)
        except Exception as e:
            print(f"[ERROR]: Could not load standardFieldName label encoder: {e}")

        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "tokenizers",
                "label_encoder_required.pickle"
            )
            with open(path, 'rb') as handle:
                self.label_encoder_required = pickle.load(handle)
        except Exception as e:
            print(f"[ERROR]: Could not load 'required' label encoder: {e}")

        self.tokenizers_loaded = True
        print("[INFO]\tTokenizers loaded successfully.")

    @staticmethod
    def clean_asset_name(name):
        replacements = {
            r"\bAHU-": "AHU ",
            r"\bAC-": "AC ",
            r"\bACU-": "ACU ",
            r"\bMAU-": "MAU ",
            r"\bFCU-": "FCU ",
            r"\bFC-": "FC ",
            r"\bEF-": "EF ",
            r"\bTF-": "TF ",
            r"\bGEF-": "GEF ",
            r"\bKEF-": "KEF ",
            r"\bCRAC-": "CRAC ",
            r"\bVAV CO\b": "VAVCO",
            r"\bVAV RH\b": "VAVRH",
            r"\bVAVCO-": "VAVCO ",
            r"\bVAVRH-": "VAVRH ",
            r"WP-": "WP ",
        }

        for pattern, repl in replacements.items():
            name = re.sub(pattern, repl, name)
        return name



    @staticmethod
    def preprocess_inputs(inputs: pd.DataFrame, feature_cols: list) -> pd.Series:
        NON_ASCII_PATTERN = r"[^\x20-\x7E]"
        SYMBOLS_PATTERN = r"[#'&:/()?,+\\]"

        missing_cols = [_ for _ in feature_cols if _ not in inputs.columns]
        
        if len(missing_cols) > 0:
            raise KeyError(f"Missing required columns: {', '.join(missing_cols)}")

        inputs = inputs[feature_cols].copy()
        inputs.fillna("", inplace=True)

        inputs.loc[:, 'inputs'] = inputs[feature_cols].apply(lambda x: " ".join(x.astype(str)), axis=1)
        inputs.loc[:, 'inputs'] = inputs.inputs.apply(lambda x: re.sub(SYMBOLS_PATTERN, "", x))
        inputs.loc[:, 'inputs'] = inputs.inputs.apply(lambda x: re.sub(NON_ASCII_PATTERN, "", x)).str.strip()

        return inputs['inputs']
    
    @staticmethod
    def encode_sequences(sequences: pd.Series, tokenizer, max_seq_length=180): # sequence length=180 was used in training
        """
        Turns a string into a sequence of indices using a pretrained tokenizer.
        Args:
        sequences: pandas Series with input text
        tokenizer: text tokenizer instance (tensorflow.keras.preprocessing.text.Tokenizer) from .pickle
        top_n: top n labels
        Returns: a dictionary: predcited label with predicted probability, and top_n predicted labels ordered by probability in ascending order
        """
        tonekized_sequences = tokenizer.texts_to_sequences(sequences)
        padded_sequences = tf.keras.preprocessing.sequence.pad_sequences(tonekized_sequences,
                                                                        maxlen=max_seq_length,
                                                                        padding='post',
                                                                        truncating='post')
        return padded_sequences
    
    @staticmethod
    def decode_binary(model_outputs, encoder):
        class_probabilities = tf.reduce_max(model_outputs, axis=1)
        class_probabilities = tf.round(class_probabilities * 100) / 100
        class_indices = tf.argmax(model_outputs, axis=1)
        class_labels = encoder.inverse_transform(class_indices)
        return class_labels, class_probabilities

    @staticmethod
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
    
    @staticmethod
    def decode_multiclass_binary(model_outputs, encoder):
        label_map = encoder.classes_
        def decode(class_vector):
            if len(class_vector) > 0:
                return ','.join([label_map[i] for i, prob in enumerate(class_vector.tolist()) if prob > 0.7])
            else: return np.nan
        labels = [decode(o) for o in model_outputs]
        return labels
    
    def get_predictions(self, df: pd.DataFrame, input_cols: list = None):
        """
        Build a load sheet from the inputs DataFrame.
        Args:
            inputs: pandas DataFrame with input data
        Returns: a dictionary with the load sheet
        """
        if not self.models_loaded or not self.tokenizers_loaded:
            raise RuntimeError("Models and tokenizers must be loaded before building the load sheet.")
        

        std_prediction_headers = load.Loadsheet._to_std_headers(load._ML_PREDICTION_HEADERS)

        header_map  ={}
        for orig, std in zip(load._ML_PREDICTION_HEADERS, std_prediction_headers):
            header_map[orig] = std

        for h in std_prediction_headers:
            if h not in df.columns:
                df[h] = None

        inputs = self.preprocess_inputs(inputs=df, feature_cols=input_cols)
        inputs = self.encode_sequences(inputs, self.tokenizer)

        required_predicted = self.required_model.predict(inputs)

        df[header_map['required']], df[header_map['required_conf']] = self.decode_binary(required_predicted, self.label_encoder_required)
        required_idx = df.index[df[header_map['required']]=="YES"]

        standardfieldname_predicted = self.standardfieldname_model.predict(inputs[required_idx])

        standardfieldname_labels, standardfieldname_probs, standardfieldname_alt = self.decode_sparse_categorical(standardfieldname_predicted, 
                                                                                                            self.label_encoder_standardFieldName)

        df.loc[required_idx, header_map['standardFieldName']] = standardfieldname_labels
        df.loc[required_idx, header_map['standardFieldName_conf']] = standardfieldname_probs
        df.loc[required_idx, header_map['standardFieldName_alt']] = standardfieldname_alt

        generaltype_predicted = self.generalType_model.predict(inputs[required_idx])
        df.loc[required_idx, header_map['generalType']] = self.decode_multiclass_binary(generaltype_predicted, self.binarizer_generalType)

        df[header_map['generalType']] = df[header_map['generalType']].apply(lambda x: x.split(",") if isinstance(x, str) else [])
        df = df.explode(header_map['generalType'], ignore_index=True)
        df[header_map['assetName']] = df[header_map['assetName']].apply(lambda x: self.clean_asset_name(x) if isinstance(x, str) else None)

        return df

if __name__ == "__main__":
    pass