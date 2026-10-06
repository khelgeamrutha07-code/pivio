# Machine learning basics interview questions

Q: Explain the bias-variance trade-off.
A: High bias means underfitting from an overly simple model; high variance means overfitting to noise. Good models balance them, using regularization, more data or cross-validation.

Q: How do you detect and prevent overfitting?
A: A large gap between training and validation scores signals it. Use cross-validation, regularization, simpler models, early stopping, dropout and more data.

Q: Precision, recall and F1: when does each matter?
A: Precision is the share of predicted positives that are correct; recall is the share of actual positives found. F1 is their harmonic mean. Favor recall for fraud or disease screening, precision when false alarms are costly.

Q: Why is accuracy misleading on imbalanced data?
A: A model predicting only the majority class can score high accuracy yet be useless. Use precision-recall, F1, ROC-AUC or PR-AUC, and resampling or class weights.

Q: What is cross-validation?
A: Splitting data into k folds, training on k-1 and validating on the remaining one in rotation, to get a more reliable performance estimate than a single split.

Q: What is data leakage?
A: When information from outside the training data, such as test rows or future values, influences the model, inflating scores. Split first, fit scalers and encoders only on training data.

Q: L1 versus L2 regularization?
A: L1 adds absolute weights penalty and drives some to zero, giving sparsity and feature selection. L2 adds squared penalty and shrinks weights smoothly.

Q: How does a random forest work?
A: It trains many decision trees on bootstrapped samples with random feature subsets and averages their predictions, which reduces variance versus a single tree.

Q: Supervised versus unsupervised learning?
A: Supervised learning uses labelled examples to predict targets, as in classification and regression. Unsupervised learning finds structure in unlabelled data, such as clustering or dimensionality reduction.

Q: How do you handle missing values?
A: First understand why they are missing. Options include dropping, mean or median imputation, model-based imputation and missing-indicator features, always fitted on training data only.

Q: Explain gradient descent.
A: An iterative optimizer that updates parameters opposite the gradient of the loss, scaled by a learning rate. Variants include SGD, mini-batch and Adam.

Q: How would you choose and evaluate a model for a new problem?
A: Define the business metric, start with a simple baseline, split data properly, compare candidates with cross-validation, inspect errors, and monitor the model after deployment.
