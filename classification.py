import pandas as pd 
import numpy as np
import re 
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from scipy.sparse import csr_matrix, hstack

class TextClassification:

    def __init__(self, df: pd.DataFrame, text_col: str):

        self.df = df
        self.text_col = text_col

        print('Sample Size', len(df))

    def encode_positive_rating(self, rating_col_name: str):

        # Drop missing values
        self.df.dropna(inplace=True)

        # Remove any 'neutral' ratings equal to 3
        self.df = self.df[self.df[rating_col_name] != 3]

        # Encode any rating above 3 to be 'positive' 
        # Encode any rating below 3 to be 'negative' 
        self.df['Positively Rated'] = np.where(self.df['Rating'] > 3, 1, 0)

        return self.df 
    
    def spliting_train_testing_binary_class(self, sample_df, encoded_label_col: str): 
        # Validation: spam_label_col needs to be encoded as 0 or 1, where 1 is a spam 
        if not all(label in [0, 1] for label in sample_df[encoded_label_col]):
            raise ValueError("All values in encoded_label_col must be either 0 or 1.")
        
        # Spliting training and testing data 
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(sample_df[self.text_col],  sample_df[encoded_label_col], random_state=0)

        # Segmentation based on binary classification 
        self.class_1 = sample_df[sample_df[encoded_label_col] == 1]
        self.class_0 = sample_df[sample_df[encoded_label_col] == 0]

        # Calculate percentage
        class_1_pct = len(self.class_1) / len(sample_df)
        class_0_pct = len(self.class_0) / len(sample_df)

        print(f'Sample size of Class 1 data: {len(self.class_1)}; Percentage: {class_1_pct:.2%}\n' 
              f'Sample size of Class 0 data: {len(self.class_0)}; Percentage: {class_0_pct:.2%}') 
        
        return self.class_1, self.class_0
   

    # Feature Engineering 

    # This function combines new features into the training data 

    def add_feature(self, X, feature_to_add):  
        """
        Returns sparse feature matrix with added feature.
        feature_to_add can also be a list of features.
        """
        return hstack([X, csr_matrix(feature_to_add).T], 'csr')
    
    def extract_nonword_char(self, text):
        return ''.join(re.findall(r'\W', text))
    

    
    def calculate_avg_nonword_char(self, name_of_text_col: str):
        
         #Count non-word characters 
        nonword_in_spam_count = self.class_1[name_of_text_col].str.count(r'\W')
        nonword_in_nonspam_count = self.class_0[name_of_text_col].str.count(r'\W')

        print('Average number of non-word characters in class 1 data',  nonword_in_spam_count.mean(), 
            '\nAverage number of non-word characters in class 0 data', nonword_in_nonspam_count.mean())
        
        # Non-word extracion 
        nonword_in_spam = self.class_1[name_of_text_col].apply(self.extract_nonword_char)
        nonword_in_nonspam = self.class_0[name_of_text_col].apply(self.extract_nonword_char)

        # Convert to DataFrame
        nonword_in_spam_df = pd.DataFrame({'nonword_char': nonword_in_spam})
        nonword_in_nonspam_df = pd.DataFrame({'nonword_char': nonword_in_nonspam})
        
        return nonword_in_spam_df, nonword_in_nonspam_df

    # Count Vectorizer 

    # Helper: Count Vectorizer with feature names as output 
    def get_feature_names_from_CountVectorizer(self):
        vect = CountVectorizer().fit(self.X_train)
        feature_names = vect.get_feature_names_out()
        print('Number of features:', len(feature_names) ) 
        return feature_names


    # Count Vectorizer with multinomial Naive Bayes classifier model

    def NB_classifier_count_vectorizer(self):

        vect = CountVectorizer().fit(self.X_train)
        X_train_vectorized = vect.transform(self.X_train)
        
        clf = MultinomialNB(alpha=0.1)
        clf.fit(X_train_vectorized, self.y_train)
        predictions = clf.predict_proba(vect.transform(self.X_test))
        auc_score = roc_auc_score(self.y_test, predictions[:,1])
        print('AUC, multinomial Naive Bayes classifier model w/ Count Vectorizer', auc_score)
        return vect 
    
    # Smallest and Largest Coefficients for Count Vectorizer 


    def return_coef(self, count_vect, model_with_count_vect):

        # Retrieve feature names from CountVectorizer
        feature_names = np.array(count_vect.get_feature_names_out())

        # Sort coefficient indices
        sorted_coef_index = model_with_count_vect.coef_[0].argsort()
        
        # Retrieve smallest and largest coefficients 
        smallest_coefs = feature_names[sorted_coef_index[:10]].tolist()
        largest_coefs = feature_names[sorted_coef_index[:-11:-1]].tolist()

        print('Smallest coefficients:', smallest_coefs,
            '\nLargest coefficients:', largest_coefs)
        
        return None
    

    # TFI-DF 

    def get_tfidf_vectorizer(self, min_df: int):

        # ignoring terms that have a document frequency strictly lower than **3**.
        vect = TfidfVectorizer(min_df=min_df).fit(self.X_train)  

        # Compress to sparse row matrix 
        X_train_vectorized = vect.transform(self.X_train)

        return vect,  X_train_vectorized 

    
    def NB_classfier_tfidf(self, tfidf_vect, tfidf_X_train_vectorized):
        
        clf = MultinomialNB(alpha=0.1)
        clf.fit(tfidf_X_train_vectorized, self.y_train)
        predictions = clf.predict_proba(tfidf_vect.transform(self.X_test))
        auc_score = roc_auc_score(self.y_test, predictions[:,1])
        print('AUC, multinomial Naive Bayes classifier model w/ TFI-DF Vectorizer', auc_score)

        return None


    def get_tfidf_features(self, tfidf_vect, num_of_smallest_features: int, num_of_largest_features: int):

        """ This function return a tuple of two series

            (smallest tf-idfs series, largest tf-idfs series)
        """

        feature_names = tfidf_vect.get_feature_names_out()
        
        #Compress to sparse row matrix 
        X_train_vectorized = tfidf_vect.transform(self.X_train)
        
        #Find the maximum tf-idf value for every feature
        max_tfidf_values =  X_train_vectorized.max(axis=0).toarray()[0]
        
        #Create a dictionary to store feature names and corresponding tf-idf values
        feature_tfidf_dict = {}
        for feature_name, tfidf_value in zip(feature_names, max_tfidf_values):
            feature_tfidf_dict[feature_name] = tfidf_value
        
        #Sort the dictionary by tf-idf values 
        sorted_features = sorted(feature_tfidf_dict.items(), key=lambda x: (x[1], x[0]))
        
        #Create a pandas Series for the smallest tf-idfs
        smallest_series = pd.Series({feat: tfidf for feat, tfidf in sorted_features[:num_of_smallest_features]})
        largest_series = pd.Series({feat: tfidf for feat, tfidf in sorted_features[-num_of_largest_features:][::-1]})
        
        return (smallest_series, largest_series)

    # SVM 

    def Tfidf_Vector_with_SVM(self, min_df: int):

        # Fit the training data using a TFIDFVectorizer
        vect = TfidfVectorizer(min_df=min_df).fit(self.X_train)
        X_train_vectorized = vect.transform(self.X_train)
        
        #Add the length of documents as an additional feature
        X_train_with_length = self.add_feature(X_train_vectorized, [len(doc) for doc in self.X_train])

        clf = SVC(C=10000) # fit a Support Vector Classification model with regularization `C=10000`
        clf.fit(X_train_with_length, self.y_train)
        
        # Same processing for test data
        X_test_vectorized = vect.transform(self.X_test)
        X_test_with_length = self.add_feature(X_test_vectorized, [len(doc) for doc in self.X_test])
        
        # Target Score 
        target_scores = clf.decision_function(X_test_with_length)

        auc_score = roc_auc_score(self.y_test, target_scores)

        print("AUC, SVM using TF-IDF and document length as additional feature:", auc_score)
        
        return None 

    

# Logistic Regression 
    
    def logistic_regressions_count_vect(self):

        vect = CountVectorizer()
        # transform the documents in the training data to a document-term matrix
        X_train_vectorized = vect.fit_transform(self.X_train)    

        # Train the model
        model = LogisticRegression()
        model.fit(X_train_vectorized, self.y_train)

        # Predict the transformed test documents
        predictions = model.predict_proba(vect.transform(self.X_test))
        auc_score = roc_auc_score(self.y_test, predictions[:,1])

        print('AUC, Logistic Regressions using Count Vectorizer', auc_score)

        self.return_coef(vect, model)

        return None 

    
    
    def logistic_regressions_count_vect_ngrams(self, top_n_rows_for_training: int):

        training_set = self.X_train[:top_n_rows_for_training]

        # Pass in `analyzer='char_wb'` which creates character n-grams only from text inside word boundaries. This should make the model more robust to spelling mistakes.
        vect = CountVectorizer(min_df=5, ngram_range=(2,5), analyzer='char_wb')
        X_train_vectorized = vect.fit_transform(training_set)
        
        # Add the length of documents as an additional feature
        X_train_with_length = self.add_feature(X_train_vectorized, [len(doc) for doc in training_set])
        
        # Add the number of digits per document as additional feature
        digits_per_doc = [text.count(r'\d') for text in training_set]
        X_train_updated_with_digits_count = self.add_feature(X_train_with_length, digits_per_doc)
        
        # non-word character
        non_word_char = [text.count(r'\W') for text in training_set]
        X_train_updated_with_nonword_char= self.add_feature(X_train_updated_with_digits_count, non_word_char)
        
        model = LogisticRegression(C=100, max_iter=1000)
        model.fit(X_train_updated_with_nonword_char, self.y_train[:top_n_rows_for_training])
        
        # Apply same processing to test data 
        X_test_vectorized = vect.transform(self.X_test)
        X_test_with_length = self.add_feature(X_test_vectorized, [len(doc) for doc in self.X_test])
        test_digits_per_doc = [text.count(r'\d') for text in self.X_test]
        X_test_with_digits = self.add_feature(X_test_with_length, test_digits_per_doc)
        test_non_word_char = [text.count(r'\W') for text in self.X_test]
        X_test_with_features = self.add_feature(X_test_with_digits, test_non_word_char)
        
        #Evaluation
        predictions = model.predict_proba(X_test_with_features)[:,1]
        auc_score = roc_auc_score(self.y_test, predictions)

        print('AUC, Logistic Regressions w/ Count Vectorizer, adding 3 features:', auc_score, 
            '\nFeatures added - 1) length of document 2) num of digits per document 3) num of non-word characters')

        return vect, model 
    

    def logistic_regression_Tfidf(self):

        # Fit the TfidfVectorizer to the training data specifiying a minimum document frequency of 5
        vect = TfidfVectorizer(min_df=5).fit(self.X_train)
        print('Number of features:', len(vect.get_feature_names_out()) ) 

        X_train_vectorized = vect.transform(self.X_train)

        model = LogisticRegression()
        model.fit(X_train_vectorized, self.y_train)

        predictions = model.predict_proba(vect.transform(self.X_test))
        auc_score = roc_auc_score(self.y_test, predictions[:,1])

        print('AUC, Logistic Regressions w/TF-IDF Vectorizer', auc_score)
              
        return None 
        
    
    def logistic_regression_Tfidf_ngrams(self):

        """
        Tfidf Vectorizer: document frequency < 5 and word N-grams from n=1 to n=3 (unigrams, bigrams, and trigrams).
        Additional Features: 
        1. the length of document (number of characters)
        2. number of digits per document

        fit a Logistic Regression model with regularization `C=100` and `max_iter=1000`
        """ 

        vect = TfidfVectorizer(min_df=5, ngram_range=(1,3)).fit(self.X_train)
        X_train_vectorized = vect.transform(self.X_train)
                            
        #Add the length of documents as an additional feature
        X_train_with_length = self.add_feature(X_train_vectorized, [len(doc) for doc in self.X_train])
        
        #Add the number of digits per document as additional feature
        digits_per_doc = [text.count(r'\d') for text in self.X_train]
        X_train_with_features = self.add_feature(X_train_with_length, digits_per_doc)
        
        model = LogisticRegression(C=100, max_iter=1000)
        model.fit(X_train_with_features, self.y_train)
        
        # Same processing for test data 
        X_test_vectorized = vect.transform(self.X_test)
        X_test_with_length = self.add_feature(X_test_vectorized, [len(doc) for doc in self.X_test])
        digits_per_doc_test = [text.count(r'\d') for text in self.X_test]
        X_test_with_features = self.add_feature(X_test_with_length, digits_per_doc_test)
        
        #Evaluation
        predictions = model.predict_proba(X_test_with_features)

        auc_score = roc_auc_score(self.y_test, predictions[:,1])

        print('AUC, Logistic Regression w/ Tfidf and document length + num of digits per document as additional features', auc_score)
        
        return None 
