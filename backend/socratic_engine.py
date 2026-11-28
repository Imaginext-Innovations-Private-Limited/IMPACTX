import logging
import requests

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:1.5b"

# ============================================================================
# 3-TIER CURRICULUM PLANS: Easy (1), Medium (2), Hard (3)
# ============================================================================

CURRICULUM_PLANS = {
    "unsupervised learning": [
        {
            "easy": {
                "question": "What is unsupervised learning in simple terms, and why does it not need a human teacher to label data?",
                "hint": "Think of sorting coins or marbles without anyone telling you their names beforehand.",
                "keywords": ["unlabel", "label", "pattern", "group", "sort", "cluster", "hidden", "no teacher"]
            },
            "medium": {
                "question": "How does unsupervised clustering differ fundamentally from supervised classification when processing new data?",
                "hint": "Classification predicts known category boundaries, while clustering discovers unknown group structures based on distance.",
                "keywords": ["distance", "boundary", "group", "unknown", "label", "target", "cluster", "similarity"]
            },
            "hard": {
                "question": "Why is the objective function of K-Means non-convex, and what mathematical problem does this create regarding local minima?",
                "hint": "K-Means minimizes within-cluster sum of squares (WCSS), but random centroid initialization can trap it in suboptimal local minima.",
                "keywords": ["wcss", "local minima", "convex", "initializ", "centroid", "sum of squares", "k-means++", "optimiz"]
            }
        },
        {
            "easy": {
                "question": "Can you give one simple everyday example where grouping unlabeled data is useful (like in online shopping)?",
                "hint": "Think about grouping shoppers by their buying habits into customer segments.",
                "keywords": ["customer", "shopping", "segment", "recommend", "group", "product", "purchase"]
            },
            "medium": {
                "question": "In customer market segmentation, what mathematical metrics determine whether two customer profiles belong to the same cluster?",
                "hint": "Algorithms measure feature proximity using distance metrics like Euclidean, Manhattan, or Cosine similarity.",
                "keywords": ["euclidean", "manhattan", "cosine", "distance", "metric", "similarity", "feature", "vector"]
            },
            "hard": {
                "question": "How does high-dimensional feature sparsity affect distance metrics in clustering, commonly known as the 'Curse of Dimensionality'?",
                "hint": "In high dimensions, the distance between any two random points converges to roughly the same value, degrading distance-based clustering.",
                "keywords": ["curse", "dimension", "sparsity", "distance", "equidistant", "converge", "volume", "pca", "density"]
            }
        },
        {
            "easy": {
                "question": "What does the K-Means algorithm do when you tell it that K = 3?",
                "hint": "It partitions the entire dataset into exactly 3 distinct clusters.",
                "keywords": ["3", "three", "cluster", "group", "partition", "k", "split"]
            },
            "medium": {
                "question": "Walk through the two alternating steps of K-Means: the Assignment step and the Update step.",
                "hint": "First assign each point to the nearest centroid, then recompute each centroid as the average position of its assigned points.",
                "keywords": ["assign", "update", "nearest", "centroid", "average", "mean", "recalculat", "distance"]
            },
            "hard": {
                "question": "How does the K-Means++ algorithm modify the initial centroid selection process to mathematically guarantee faster convergence?",
                "hint": "It chooses the first centroid uniformly at random and subsequent centroids with probability proportional to their squared distance from existing centroids.",
                "keywords": ["k-means++", "probabilit", "squared distance", "spread", "initializ", "furthest", "converge", "wcss"]
            }
        },
        {
            "easy": {
                "question": "What is 'dimensionality reduction' in machine learning, and why would we want fewer features?",
                "hint": "It reduces the number of variables while preserving the most important information, making models faster and easier to plot.",
                "keywords": ["reduc", "feature", "variable", "plot", "visualiz", "compress", "fewer", "speed"]
            },
            "medium": {
                "question": "What does Principal Component Analysis (PCA) actually find when it computes the first principal component of a dataset?",
                "hint": "It finds the orthogonal vector direction along which the variance of the data is maximized.",
                "keywords": ["variance", "direction", "orthogonal", "vector", "maximiz", "axis", "spread", "project"]
            },
            "hard": {
                "question": "Explain how the Covariance Matrix, Eigenvectors, and Eigenvalues are mathematically used to construct principal components in PCA.",
                "hint": "Eigenvectors of the covariance matrix define the orthogonal directions of variance, and their eigenvalues determine the proportion of variance explained.",
                "keywords": ["covariance", "eigenvector", "eigenvalue", "matrix", "diagonal", "orthogonal", "variance", "transform"]
            }
        },
        {
            "easy": {
                "question": "What is an 'outlier' or 'anomaly' in a dataset, and why is detecting it important in bank transactions?",
                "hint": "An anomaly is an unusual data point that looks completely different from normal patterns, often indicating credit card fraud.",
                "keywords": ["outlier", "fraud", "unusual", "deviat", "rare", "normal", "bank", "credit card"]
            },
            "medium": {
                "question": "How does an unsupervised anomaly detection model identify fraud if it has never seen labeled fraud cases before?",
                "hint": "It models the distribution or density of normal behavior; points falling into low-density regions or far from clusters are flagged.",
                "keywords": ["density", "distribution", "normal", "deviat", "distance", "threshold", "low", "region"]
            },
            "hard": {
                "question": "How does the Isolation Forest algorithm isolate anomalies using binary partitioning trees, and why are anomalies isolated with shorter paths?",
                "hint": "Anomalies are few and attribute-different, so random recursive splits isolate them near the root of the tree with short average path lengths.",
                "keywords": ["isolation forest", "tree", "split", "path length", "depth", "partition", "root", "anomaly score"]
            }
        },
        {
            "easy": {
                "question": "What is a 'dendrogram' in Hierarchical Clustering, and what does it look like?",
                "hint": "It is a tree-like diagram that visually illustrates how data points and clusters merge at different levels.",
                "keywords": ["tree", "diagram", "merge", "hierarch", "branch", "level", "visual"]
            },
            "medium": {
                "question": "What is the difference between Agglomerative (bottom-up) and Divisive (top-down) hierarchical clustering?",
                "hint": "Agglomerative starts with each point as its own cluster and merges them; Divisive starts with one giant cluster and splits it.",
                "keywords": ["agglomerative", "divisive", "bottom-up", "top-down", "merge", "split", "single"]
            },
            "hard": {
                "question": "Compare Single Linkage, Complete Linkage, and Ward's method when merging clusters in Agglomerative Clustering.",
                "hint": "Single uses minimum distance (chaining effect), Complete uses maximum distance (compact spheres), and Ward's minimizes total within-cluster variance.",
                "keywords": ["single linkage", "complete linkage", "ward", "chaining", "variance", "minimum distance", "maximum distance"]
            }
        },
        {
            "easy": {
                "question": "In retail shopping carts, what does an association rule like 'If Milk, then Bread' tell a supermarket manager?",
                "hint": "Customers who buy milk are very likely to also buy bread on the same trip.",
                "keywords": ["buy", "together", "milk", "bread", "basket", "product", "frequent", "trip"]
            },
            "medium": {
                "question": "What is the difference between the 'Support' and the 'Confidence' metrics in Association Rule Mining?",
                "hint": "Support measures how frequently the items appear together overall; Confidence measures how often item Y is bought given that X was bought.",
                "keywords": ["support", "confidence", "frequency", "ratio", "probabilit", "conditional", "overall"]
            },
            "hard": {
                "question": "How does the Apriori Property (downward closure property of support) prune the search space when discovering frequent itemsets?",
                "hint": "If an itemset is infrequent, all of its supersets must also be infrequent, eliminating the need to calculate their support.",
                "keywords": ["apriori", "downward closure", "superset", "prune", "infrequent", "subset", "search space"]
            }
        },
        {
            "easy": {
                "question": "Why can you not easily calculate an 'accuracy percentage' for an unsupervised learning model?",
                "hint": "Because there are no correct answers or ground-truth labels provided in the test set to compare against.",
                "keywords": ["no label", "no answer", "ground truth", "target", "compare", "unlabel", "correct"]
            },
            "medium": {
                "question": "What does the Silhouette Score measure, and what does a score close to +1 indicate about cluster separation?",
                "hint": "It measures how similar a point is to its own cluster compared to other clusters; +1 means well-separated, dense clusters.",
                "keywords": ["silhouette", "separation", "cohesion", "+1", "similar", "dense", "boundary", "measure"]
            },
            "hard": {
                "question": "Explain the formulation of the Davies-Bouldin Index or Calinski-Harabasz Index for intrinsic clustering validation.",
                "hint": "Davies-Bouldin calculates the average similarity between each cluster and its most similar one (lower is better); Calinski-Harabasz is the ratio of between-cluster to within-cluster dispersion.",
                "keywords": ["davies-bouldin", "calinski-harabasz", "dispersion", "ratio", "between", "within", "intrinsic", "validation"]
            }
        },
        {
            "easy": {
                "question": "How does the 'Elbow Method' help you decide the best value of K for K-Means clustering?",
                "hint": "You plot cluster error against K and look for the 'elbow' bend where adding more clusters yields diminishing returns.",
                "keywords": ["elbow", "bend", "plot", "k", "error", "inertia", "wcss", "diminish", "best"]
            },
            "medium": {
                "question": "Why does the WCSS (within-cluster sum of squares) always decrease as K increases, even up to K = N?",
                "hint": "Because when K equals N, every point is its own cluster with a distance of zero, which causes total overfitting without meaningful grouping.",
                "keywords": ["decrease", "k=n", "zero", "overfit", "distance", "inertia", "sum of squares", "trivial"]
            },
            "hard": {
                "question": "When the Elbow Method produces an ambiguous smooth curve without a sharp bend, what alternative statistical method (such as the Gap Statistic) can identify optimal K?",
                "hint": "The Gap Statistic compares the change in within-cluster dispersion to an expected null reference distribution generated via uniform simulation.",
                "keywords": ["gap statistic", "null distribution", "uniform", "reference", "simulation", "dispersion", "monte carlo"]
            }
        },
        {
            "easy": {
                "question": "If you have a collection of 10,000 untagged news articles, how could unsupervised learning automatically organize them for you?",
                "hint": "It can cluster articles covering similar subjects (like sports, tech, or politics) into separate topic folders.",
                "keywords": ["topic", "cluster", "folder", "group", "article", "category", "subject", "organize"]
            },
            "medium": {
                "question": "What is Latent Dirichlet Allocation (LDA) used for in Natural Language Processing, and what are its two primary Dirichlet distributions?",
                "hint": "It is a generative probabilistic topic model that represents documents as mixtures of topics, and topics as mixtures of words.",
                "keywords": ["lda", "topic", "mixture", "document", "word", "dirichlet", "distribution", "latent"]
            },
            "hard": {
                "question": "Contrast density-based clustering (DBSCAN) with centroid-based clustering (K-Means) regarding arbitrary cluster shapes and noise handling.",
                "hint": "DBSCAN can find arbitrarily shaped clusters and labels sparse points as noise without forcing every point into a cluster, using epsilon and minPts.",
                "keywords": ["dbscan", "density", "noise", "epsilon", "minpts", "arbitrary", "shape", "spherical", "core point"]
            }
        }
    ],

    "supervised learning": [
        {
            "easy": {
                "question": "What is supervised learning in plain English, and why is it called 'supervised'?",
                "hint": "Think of learning from a teacher who provides flashcards with questions on the front and correct answers on the back.",
                "keywords": ["teacher", "label", "answer", "supervis", "target", "known", "flashcard"]
            },
            "medium": {
                "question": "In a supervised dataset, explain how input 'features' are mathematically mapped to the target 'label'.",
                "hint": "The algorithm learns a mapping function f(X) that approximates the true output Y with minimum error.",
                "keywords": ["mapping", "function", "feature", "x", "y", "label", "input", "output", "target"]
            },
            "hard": {
                "question": "Formulate the supervised empirical risk minimization (ERM) problem and explain why we optimize surrogate loss functions instead of 0-1 loss.",
                "hint": "0-1 loss is non-convex and non-differentiable (NP-hard to optimize), so we use convex, smooth surrogates like cross-entropy or hinge loss.",
                "keywords": ["empirical risk", "0-1 loss", "convex", "differentiable", "gradient", "cross-entropy", "surrogate", "hinge"]
            }
        },
        {
            "easy": {
                "question": "Can you name two simple real-world examples of supervised learning you interact with every day?",
                "hint": "Think of spam filtering in your email inbox or predictive text on your phone.",
                "keywords": ["spam", "email", "weather", "house", "price", "face", "voice", "predict"]
            },
            "medium": {
                "question": "What is the key difference between a Classification problem and a Regression problem?",
                "hint": "Classification outputs discrete categories (like yes/no), while regression outputs continuous numeric values (like temperature).",
                "keywords": ["classification", "regression", "discrete", "continuous", "category", "numeric", "number"]
            },
            "hard": {
                "question": "In logistic regression, why do we apply the sigmoid/logistic link function to the linear combination of inputs instead of fitting linear regression directly to binary outcomes?",
                "hint": "Linear regression can output values outside [0, 1] and violates homoscedasticity, whereas sigmoid bounds outputs to valid probabilities between 0 and 1.",
                "keywords": ["sigmoid", "probability", "0 and 1", "bound", "odds", "logit", "linear regression", "violat"]
            }
        },
        {
            "easy": {
                "question": "If you want to train an algorithm to recognize pictures of cats and dogs, what must you feed into the training process?",
                "hint": "You need pictures of cats and dogs labeled with their correct names.",
                "keywords": ["picture", "image", "label", "cat", "dog", "name", "tag", "photo"]
            },
            "medium": {
                "question": "Why is it dangerous to evaluate your model on the exact same dataset that you used for training?",
                "hint": "The model could simply memorize the training examples without learning how to generalize to new, unseen cases.",
                "keywords": ["memoriz", "overfit", "unseen", "generaliz", "test", "evaluat", "bias", "cheat"]
            },
            "hard": {
                "question": "Explain the mathematical trade-off between Bias and Variance in supervised learning models.",
                "hint": "High bias leads to underfitting (oversimplified assumptions), high variance leads to overfitting (sensitivity to noise), and expected test error is irreducible error + bias² + variance.",
                "keywords": ["bias", "variance", "trade-off", "underfit", "overfit", "irreducible error", "decomposition", "complexity"]
            }
        },
        {
            "easy": {
                "question": "What does 'overfitting' mean in simple words?",
                "hint": "The model learns the training data too well, including mistakes and noise, so it fails on new questions.",
                "keywords": ["overfit", "memoriz", "noise", "fail", "new", "unseen", "too well"]
            },
            "medium": {
                "question": "What are two practical techniques developers use to prevent a model from overfitting on training data?",
                "hint": "Techniques include cross-validation, regularization (L1/L2), pruning decision trees, or collecting more training data.",
                "keywords": ["regularization", "cross-validation", "dropout", "pruning", "l1", "l2", "more data", "early stopping"]
            },
            "hard": {
                "question": "Compare L1 (Lasso) and L2 (Ridge) regularization regarding weight shrinkage and feature sparsity.",
                "hint": "L1 adds the absolute sum of weights inducing exact zero sparsity (feature selection); L2 adds squared weights shrinking weights smoothly toward zero.",
                "keywords": ["l1", "l2", "lasso", "ridge", "sparsity", "zero", "absolute", "squared", "penalty", "shrink"]
            }
        },
        {
            "easy": {
                "question": "Name one simple supervised machine learning algorithm you have heard of.",
                "hint": "Examples include Decision Tree, Linear Regression, or K-Nearest Neighbors (KNN).",
                "keywords": ["decision tree", "linear", "logistic", "knn", "random forest", "svm", "neural"]
            },
            "medium": {
                "question": "How does a K-Nearest Neighbors (KNN) classifier determine the category for a brand-new test point?",
                "hint": "It finds the K closest training points in feature space and picks the majority class among them.",
                "keywords": ["k", "nearest", "neighbor", "distance", "majority", "vote", "closest", "class"]
            },
            "hard": {
                "question": "Why is KNN computationally expensive at inference time, and why is feature scaling (like normalization) mandatory for distance-based algorithms?",
                "hint": "KNN is a lazy learner that stores all data and computes distances O(N*D) at test time; unscaled features with large numerical ranges will dominate the Euclidean distance.",
                "keywords": ["lazy learner", "inference", "o(n)", "scale", "normalization", "euclidean", "dominate", "standardization"]
            }
        },
        {
            "easy": {
                "question": "What is the purpose of a 'loss function' when training a machine learning model?",
                "hint": "It measures how big of a mistake the model made so it can correct itself.",
                "keywords": ["mistake", "error", "difference", "measure", "correct", "loss", "penalty", "improve"]
            },
            "medium": {
                "question": "How does Gradient Descent use the derivative of the loss function to update the model's weights?",
                "hint": "It computes the gradient slope and takes small steps in the opposite direction to move toward the minimum loss.",
                "keywords": ["gradient", "derivative", "slope", "weight", "learning rate", "step", "minimum", "opposite"]
            },
            "hard": {
                "question": "Explain the difference between Batch Gradient Descent, Stochastic Gradient Descent (SGD), and Mini-Batch Gradient Descent regarding convergence stability and memory.",
                "hint": "Batch uses the entire dataset (stable but slow/memory intensive); SGD updates per sample (fast, noisy, escapes saddle points); Mini-batch balances both with matrix vectorization.",
                "keywords": ["batch", "stochastic", "mini-batch", "noise", "convergence", "variance", "vectoriz", "epoch", "sample"]
            }
        },
        {
            "easy": {
                "question": "What is a 'decision tree', and how does it make a decision similar to a flowchart?",
                "hint": "It asks a series of true/false questions about the data until it reaches an answer at the bottom.",
                "keywords": ["tree", "flowchart", "question", "split", "branch", "leaf", "true", "false", "rule"]
            },
            "medium": {
                "question": "What criteria (such as Information Gain, Entropy, or Gini Impurity) does a Decision Tree use to pick the best feature to split on?",
                "hint": "It chooses the split that maximizes purity by achieving the greatest reduction in entropy or Gini impurity.",
                "keywords": ["entropy", "gini", "information gain", "purity", "split", "reduc", "impurity"]
            },
            "hard": {
                "question": "How does Random Forest use Bagging (Bootstrap Aggregation) and Random Feature Subspacing to decorrelate individual trees and reduce ensemble variance?",
                "hint": "Bagging trains trees on random bootstrap samples with replacement, and evaluating only a random subset of features (sqrt(D)) per split prevents dominant features from creating correlated trees.",
                "keywords": ["bagging", "bootstrap", "replacement", "decorrelate", "variance", "subset", "random forest", "feature"]
            }
        },
        {
            "easy": {
                "question": "Why is testing on unseen data with K-Fold Cross-Validation better than doing just a single train/test split?",
                "hint": "It splits data into multiple folds and tests on every fold once, giving a much more reliable score.",
                "keywords": ["fold", "reliable", "split", "multiple", "average", "unseen", "test", "every"]
            },
            "medium": {
                "question": "What is Stratified K-Fold Cross-Validation, and why is it essential for imbalanced classification tasks?",
                "hint": "It ensures that each fold maintains the same percentage proportion of target classes as the complete dataset.",
                "keywords": ["stratified", "proportion", "percentage", "imbalanced", "class", "ratio", "fold", "represent"]
            },
            "hard": {
                "question": "How does data leakage occur during cross-validation if preprocessing (like feature scaling or target encoding) is executed before splitting folds?",
                "hint": "Computing statistics like mean and variance across the full dataset leaks information from validation folds into training folds, causing overly optimistic validation performance.",
                "keywords": ["data leakage", "leak", "preprocessing", "scale", "pipeline", "fold", "validation", "optimistic", "statistics"]
            }
        },
        {
            "easy": {
                "question": "If your model gets 99% accuracy on detecting a rare disease that only 1 person in 1,000 has, why might that score be deceiving?",
                "hint": "A dumb model that just predicts 'No Disease' for everyone would still achieve 99.9% accuracy while helping no one.",
                "keywords": ["rare", "disease", "deceiv", "mislead", "all no", "everyone", "dumb", "imbalance"]
            },
            "medium": {
                "question": "Explain the difference between Precision and Recall using the example of an email spam detector.",
                "hint": "Precision is how many flagged emails were actually spam; Recall is how many of all actual spam emails were successfully caught.",
                "keywords": ["precision", "recall", "false positive", "false negative", "flagged", "actual", "spam"]
            },
            "hard": {
                "question": "Explain how the Receiver Operating Characteristic (ROC) curve and Area Under the Curve (AUC) evaluate classification thresholds independently of class prevalence.",
                "hint": "ROC plots True Positive Rate against False Positive Rate across all discrimination thresholds; AUC measures the probability that a random positive is ranked higher than a random negative.",
                "keywords": ["roc", "auc", "tpr", "fpr", "threshold", "rank", "prevalence", "true positive", "false positive"]
            }
        },
        {
            "easy": {
                "question": "What is the difference between a model's 'parameters' and its 'hyperparameters'?",
                "hint": "Parameters are learned by the computer from data; hyperparameters are settings you choose before training starts.",
                "keywords": ["parameter", "hyperparameter", "learned", "setting", "config", "manual", "choose", "computer"]
            },
            "medium": {
                "question": "What is the difference between Grid Search and Random Search for hyperparameter tuning?",
                "hint": "Grid Search exhaustively evaluates every predefined combination; Random Search samples random combinations from distributions, often finding optimal values faster.",
                "keywords": ["grid search", "random search", "combination", "exhaustive", "sample", "faster", "tune"]
            },
            "hard": {
                "question": "How does Bayesian Optimization for hyperparameter tuning use a Gaussian Process surrogate model and an Acquisition Function (like Expected Improvement) to optimize search efficiency?",
                "hint": "It builds a probabilistic model of the objective function, balancing exploration of high-uncertainty areas with exploitation of promising areas to minimize expensive evaluation calls.",
                "keywords": ["bayesian", "gaussian process", "acquisition function", "exploration", "exploitation", "expected improvement", "surrogate"]
            }
        }
    ],

    "cloud computing": [
        {
            "easy": {
                "question": "What is Cloud Computing in simple terms, and why do companies use it instead of buying physical servers?",
                "hint": "It lets you rent compute power and storage over the internet on demand without maintaining a server closet.",
                "keywords": ["rent", "internet", "server", "hardware", "storage", "on-demand", "cost", "maintain"]
            },
            "medium": {
                "question": "Explain the shift from Capital Expenditures (CapEx) to Operational Expenditures (OpEx) when migrating to the cloud.",
                "hint": "Instead of huge upfront hardware investments (CapEx), companies pay recurring monthly bills for what they actually consume (OpEx).",
                "keywords": ["capex", "opex", "capital", "operational", "upfront", "pay-as-you-go", "consume", "recurring"]
            },
            "hard": {
                "question": "Analyze how multi-tenant cloud virtualization using Type-1 hypervisors vs containerization (cgroups/namespaces) enforces compute isolation and security boundaries.",
                "hint": "Hypervisors run independent guest operating systems with hardware virtualization; containers share the host kernel using namespaces and cgroups, having lower isolation overhead.",
                "keywords": ["hypervisor", "multi-tenant", "isolation", "container", "namespace", "cgroups", "kernel", "virtualization"]
            }
        },
        {
            "easy": {
                "question": "What are the three main cloud service models (IaaS, PaaS, SaaS)? Name one example of SaaS.",
                "hint": "Infrastructure as a Service, Platform as a Service, Software as a Service (e.g., Google Drive, Netflix, Gmail).",
                "keywords": ["iaas", "paas", "saas", "gmail", "google drive", "netflix", "software", "infrastructure", "platform"]
            },
            "medium": {
                "question": "In the Shared Responsibility Model, what layers does the cloud provider manage in IaaS versus PaaS?",
                "hint": "In IaaS the provider manages physical hardware/networking and you manage the OS; in PaaS the provider also manages the OS and runtime.",
                "keywords": ["shared responsibility", "os", "hardware", "runtime", "iaas", "paas", "manage", "patch"]
            },
            "hard": {
                "question": "In a cloud-native microservices architecture, how do modern API gateways handle zero-trust mutual TLS (mTLS), token introspection, and distributed rate limiting across hybrid cloud deployments?",
                "hint": "They terminate external TLS, validate JWT/OAuth tokens with identity providers, enforce mTLS between internal pods, and use shared caches (Redis) for distributed token-bucket rate limits.",
                "keywords": ["api gateway", "mtls", "zero-trust", "jwt", "oauth", "rate limit", "token", "redis", "microservice"]
            }
        },
        {
            "easy": {
                "question": "What is the difference between Public Cloud, Private Cloud, and Hybrid Cloud?",
                "hint": "Public is shared infrastructure for anyone, Private is dedicated to one organization, and Hybrid mixes both.",
                "keywords": ["public", "private", "hybrid", "dedicated", "shared", "mix", "on-premise"]
            },
            "medium": {
                "question": "Why would a bank or healthcare organization choose a Hybrid Cloud instead of a 100% Public Cloud solution?",
                "hint": "To keep sensitive customer data securely on private on-premise servers for regulatory compliance while using public cloud for scalable web apps.",
                "keywords": ["compliance", "sensitive", "regulat", "privacy", "security", "on-premise", "scale", "bank"]
            },
            "hard": {
                "question": "How do cloud Direct Connect / ExpressRoute dedicated interconnects achieve deterministic network latency, BGP route peering, and encryption compared to IPSec VPN over public transit?",
                "hint": "Dedicated physical fiber bypasses public internet congestion using private 802.1Q VLANs and eBGP peering, achieving higher throughput and predictable latency.",
                "keywords": ["direct connect", "expressroute", "bgp", "vlan", "latency", "fiber", "peering", "throughput", "transit"]
            }
        },
        {
            "easy": {
                "question": "What does 'Auto-Scaling' mean in the cloud when lots of visitors suddenly visit a website?",
                "hint": "The cloud automatically adds more servers to handle the traffic and removes them when traffic drops.",
                "keywords": ["auto-scale", "traffic", "add server", "spike", "dynamic", "visitor", "remove"]
            },
            "medium": {
                "question": "What is the technical difference between 'Scalability' and 'Elasticity' in cloud infrastructure?",
                "hint": "Scalability is the ability to handle increased load by growing; elasticity is the ability to automatically expand AND shrink in real time as demand fluctuates.",
                "keywords": ["scalability", "elasticity", "shrink", "expand", "demand", "fluctuat", "auto", "load"]
            },
            "hard": {
                "question": "How do horizontal auto-scaling policies balance cool-down periods and predictive metric tracking to prevent 'flapping' (rapid thrashing of provisioning/deprovisioning)?",
                "hint": "Cool-down timers prevent new scaling actions until newly booted instances stabilize and report metrics, while step scaling adjusts capacity based on metric deviation magnitude.",
                "keywords": ["flapping", "cool-down", "thrashing", "stabiliz", "step scaling", "hysteresis", "metric", "provision"]
            }
        },
        {
            "easy": {
                "question": "What is 'Serverless' computing (like AWS Lambda)? Does it mean there are literally no servers?",
                "hint": "Servers still exist, but you don't manage them—you just upload code and pay only when the code runs.",
                "keywords": ["serverless", "lambda", "no server", "upload code", "pay per run", "manage", "event"]
            },
            "medium": {
                "question": "What is a 'cold start' in serverless functions, and why does it cause latency spikes?",
                "hint": "When a function has not been invoked recently, the cloud must provision a new container and initialize the runtime before running code.",
                "keywords": ["cold start", "latency", "provision", "container", "runtime", "initializ", "delay", "spin up"]
            },
            "hard": {
                "question": "Compare the execution model, state persistence challenges, and connection pooling issues (e.g. database connection exhaustion) between Serverless FaaS and container orchestration (Kubernetes).",
                "hint": "Serverless functions are ephemeral and scale to hundreds of instances, exhausting relational DB connection limits unless an RDS Proxy / connection pooler is used; K8s maintains long-lived stateful pods.",
                "keywords": ["ephemeral", "connection pooling", "exhaustion", "rds proxy", "stateful", "kubernetes", "faas", "persistent"]
            }
        },
        {
            "easy": {
                "question": "What is an 'Availability Zone' (AZ) in AWS or Azure, and how does it prevent total website downtime?",
                "hint": "AZs are isolated physical data centers within a region, so if one flood or power outage occurs, other zones keep running.",
                "keywords": ["availability zone", "data center", "isolated", "outage", "downtime", "power", "region"]
            },
            "medium": {
                "question": "What is the difference between a multi-AZ deployment and a multi-Region deployment in terms of disaster recovery and latency?",
                "hint": "Multi-AZ provides local hardware fault tolerance with synchronous replication; multi-region protects against entire geographical disasters with asynchronous replication.",
                "keywords": ["multi-az", "multi-region", "synchronous", "asynchronous", "disaster", "geographical", "latency", "replication"]
            },
            "hard": {
                "question": "How do distributed databases achieve CAP theorem consistency across multi-region deployments using algorithms like Raft or Paxos, and what latency trade-offs occur with synchronous quorum writes?",
                "hint": "Synchronous quorum writes must wait for round-trip acknowledgments across speed-of-light geographic fiber distances, drastically increasing write latency to guarantee strong consistency.",
                "keywords": ["cap theorem", "paxos", "raft", "quorum", "consistency", "latency", "round-trip", "speed of light", "partition"]
            }
        },
        {
            "easy": {
                "question": "What is cloud object storage (like AWS S3), and what kinds of files is it best for storing?",
                "hint": "It stores unstructured files like images, videos, backups, and PDF documents accessed via web URLs.",
                "keywords": ["object storage", "s3", "image", "video", "file", "backup", "unstructured", "url"]
            },
            "medium": {
                "question": "How does Block Storage (like AWS EBS) differ from Object Storage (like AWS S3) in how operating systems access them?",
                "hint": "Block storage attaches directly to an instance like a local hard drive for file systems/databases; object storage stores whole objects accessed via HTTP REST APIs.",
                "keywords": ["block storage", "ebs", "s3", "hard drive", "api", "http", "filesystem", "database"]
            },
            "hard": {
                "question": "How does eventual consistency in distributed object storage impact read-after-write operations during rapid object overwrite and delete requests?",
                "hint": "While simple PUT of new objects is often strongly consistent, distributed replica propagation during simultaneous updates/deletes can return stale data until all metadata nodes synchronize.",
                "keywords": ["eventual consistency", "read-after-write", "stale", "replica", "propagation", "overwrite", "metadata", "strong consistency"]
            }
        },
        {
            "easy": {
                "question": "What is a Content Delivery Network (CDN) like Cloudflare, and how does it make web pages load faster for users across the world?",
                "hint": "It caches website content on servers located close to the user's geographic location so data travels a shorter distance.",
                "keywords": ["cdn", "cache", "close", "fast", "geographic", "edge", "location", "distance"]
            },
            "medium": {
                "question": "What is the difference between static caching and dynamic caching at a CDN Edge location?",
                "hint": "Static caching stores fixed files like images/CSS; dynamic caching optimizes API routes and edge code execution closer to the user.",
                "keywords": ["static", "dynamic", "cache", "css", "image", "api", "edge", "header", "ttl"]
            },
            "hard": {
                "question": "How does Anycast DNS routing direct user traffic to the topologically closest CDN point-of-presence (PoP), and how does BGP route poisoning mitigate DDoS attacks at edge PoPs?",
                "hint": "Anycast advertises the same IP prefix from multiple global PoPs via BGP so routers select the shortest AS path; under attack, transit routes can be community-blackholed at edge scrubbing centers.",
                "keywords": ["anycast", "bgp", "pop", "as-path", "ddos", "scrubbing", "blackhole", "routing", "prefix"]
            }
        },
        {
            "easy": {
                "question": "What is 'Infrastructure as Code' (IaC) like Terraform, and why is writing configuration files better than clicking around in a web console?",
                "hint": "You define servers and databases in code files, making setups repeatable, automated, and trackable in version control.",
                "keywords": ["iac", "terraform", "code", "repeatable", "automate", "version control", "console", "config"]
            },
            "medium": {
                "question": "What is 'configuration drift' in cloud infrastructure, and how does an IaC state file detect it?",
                "hint": "Drift happens when someone makes manual changes in the web console; IaC compares live cloud resources against its recorded state file.",
                "keywords": ["drift", "state file", "manual", "console", "compare", "detect", "change", "reconcil"]
            },
            "hard": {
                "question": "How does Terraform calculate a Directed Acyclic Graph (DAG) of resource dependencies to maximize parallel provisioning while preventing cyclic deadlocks during multi-module deployments?",
                "hint": "It inspects resource attributes and interpolation references to build a topological dependency graph, evaluating independent branches concurrently and joining on dependencies.",
                "keywords": ["dag", "directed acyclic graph", "dependency", "topological", "parallel", "deadlock", "interpolation", "terraform"]
            }
        },
        {
            "easy": {
                "question": "What is the primary role of Cloud Identity and Access Management (IAM)?",
                "hint": "It controls who is authenticated and authorized to access specific cloud resources and permissions.",
                "keywords": ["iam", "permission", "access", "role", "authorize", "authenticate", "user", "secure"]
            },
            "medium": {
                "question": "Explain the Principle of Least Privilege in cloud IAM and why granting full AdministratorAccess is dangerous.",
                "hint": "Users and services should only be granted the minimum permissions necessary to do their job, reducing attack surfaces.",
                "keywords": ["least privilege", "minimum", "permission", "attack surface", "admin", "secure", "limit"]
            },
            "hard": {
                "question": "Analyze the IAM Policy evaluation logic in AWS: how do explicit Deny, explicit Allow, Permission Boundaries, and SCPs (Service Control Policies) interact in multi-account organizations?",
                "hint": "Explicit Deny always overrides any Allow; to perform an action, the call must be allowed by the Organization SCP, within the Permission Boundary, and granted by an identity/resource policy with zero Denies.",
                "keywords": ["explicit deny", "allow", "permission boundary", "scp", "organization", "evaluation logic", "override"]
            }
        }
    ],

    "osi": [
        {
            "easy": {
                "question": "What does OSI stand for, and how many layers make up the OSI model?",
                "hint": "Open Systems Interconnection, and it consists of 7 functional layers.",
                "keywords": ["open systems", "interconnection", "7", "seven", "layer"]
            },
            "medium": {
                "question": "Can you name all 7 layers of the OSI model from bottom (Layer 1) to top (Layer 7)?",
                "hint": "Physical, Data Link, Network, Transport, Session, Presentation, Application (Please Do Not Throw Sausage Pizza Away).",
                "keywords": ["physical", "data link", "network", "transport", "session", "presentation", "application"]
            },
            "hard": {
                "question": "Why did the historical OSI 7-layer protocol stack fail in commercial adoption compared to the pragmatic 4-layer TCP/IP model in the 1980s?",
                "hint": "OSI was overly complex, had bureaucratic standards delays, and duplicate functions (e.g. flow control at layers 2 and 4), while TCP/IP was implemented and running in BSD Unix.",
                "keywords": ["tcp/ip", "complexity", "bsd unix", "adoption", "duplicate", "darpa", "pragmatic", "standards"]
            }
        },
        {
            "easy": {
                "question": "Which layer is Layer 1, and what physical hardware does it involve?",
                "hint": "The Physical Layer deals with physical cables, fiber optic glass, radio frequencies, and electrical voltages.",
                "keywords": ["physical", "layer 1", "cable", "wire", "fiber", "signal", "voltage", "pin", "hardware"]
            },
            "medium": {
                "question": "What is the Protocol Data Unit (PDU) at Layer 1, and what is the difference between attenuation and crosstalk?",
                "hint": "The PDU is 'Bits'; attenuation is signal weakening over distance, while crosstalk is electromagnetic interference from adjacent wires.",
                "keywords": ["bit", "attenuation", "crosstalk", "signal", "interference", "pdu", "weaken", "distance"]
            },
            "hard": {
                "question": "Explain the Nyquist Bit Rate formula and Shannon Channel Capacity theorem regarding maximum theoretical data throughput in the presence of noise.",
                "hint": "Nyquist gives maximum bit rate for noiseless channels C = 2B log2(M); Shannon capacity C = B log2(1 + SNR) accounts for thermal Gaussian noise.",
                "keywords": ["nyquist", "shannon", "capacity", "snr", "bandwidth", "noise", "bit rate", "thermal"]
            }
        },
        {
            "easy": {
                "question": "What does Layer 2 (Data Link Layer) use to identify a device on a local network?",
                "hint": "It uses hardware physical addresses known as MAC addresses.",
                "keywords": ["mac", "mac address", "physical address", "data link", "hardware", "switch"]
            },
            "medium": {
                "question": "How does a Layer 2 network switch learn MAC addresses and populate its MAC address table?",
                "hint": "It inspects the source MAC address of incoming frames and records which physical port that frame entered from.",
                "keywords": ["source mac", "port", "switch", "table", "learn", "incoming", "frame", "forward"]
            },
            "hard": {
                "question": "How does the Spanning Tree Protocol (STP / 802.1D) prevent broadcast storms and bridging loops in redundant Layer 2 switched topologies?",
                "hint": "Switches exchange BPDUs to elect a Root Bridge, compute shortest path costs, and place redundant backup ports into a non-forwarding (blocking) state.",
                "keywords": ["stp", "spanning tree", "bpdu", "root bridge", "blocking", "loop", "broadcast storm", "redundant"]
            }
        },
        {
            "easy": {
                "question": "What device operates at Layer 3 (Network Layer) to connect different networks, and what address does it read?",
                "hint": "Routers operate at Layer 3 and read logical IP addresses to forward packets.",
                "keywords": ["router", "ip", "ip address", "network layer", "packet", "layer 3", "logical"]
            },
            "medium": {
                "question": "What is the difference between a subnet mask and a default gateway in IPv4 routing?",
                "hint": "The subnet mask splits an IP address into network and host portions; the default gateway is the router IP used to send traffic outside the local network.",
                "keywords": ["subnet", "mask", "gateway", "router", "network", "host", "outside", "portion"]
            },
            "hard": {
                "question": "Explain how Dijkstra's Shortest Path First algorithm operates in OSPF (link-state) vs Bellman-Ford in RIP (distance-vector), and why distance-vector protocols suffer from the Count-to-Infinity problem.",
                "hint": "OSPF builds a complete synchronized topological map using LSAs and Dijkstra; RIP only knows neighbor metrics, leading to routing loops and slow convergence (mitigated by split horizon/poison reverse).",
                "keywords": ["dijkstra", "ospf", "bellman-ford", "count to infinity", "link-state", "distance-vector", "split horizon", "lsa"]
            }
        },
        {
            "easy": {
                "question": "What are the two main protocols that operate at Layer 4 (Transport Layer)?",
                "hint": "TCP and UDP.",
                "keywords": ["tcp", "udp", "transport", "layer 4"]
            },
            "medium": {
                "question": "What is the difference between TCP and UDP, and why does video streaming prefer UDP?",
                "hint": "TCP is connection-oriented and guarantees delivery with acknowledgments; UDP is connectionless and fast, prioritizing low latency over lost packets.",
                "keywords": ["tcp", "udp", "reliable", "connection", "acknowledgment", "fast", "latency", "loss", "stream"]
            },
            "hard": {
                "question": "Detail the steps of the TCP 3-Way Handshake, TCP 4-Way Teardown, and explain why the TIME_WAIT state exists.",
                "hint": "SYN -> SYN-ACK -> ACK establishes; FIN -> ACK -> FIN -> ACK tears down; TIME_WAIT (2MSL) prevents duplicate delayed packets from corrupting new connections on the same socket pair.",
                "keywords": ["syn", "ack", "fin", "time_wait", "2msl", "3-way", "handshake", "socket", "teardown"]
            }
        },
        {
            "easy": {
                "question": "What does Layer 5 (Session Layer) do in simple terms?",
                "hint": "It opens, maintains, and closes communication sessions between two applications.",
                "keywords": ["session", "open", "close", "maintain", "dialog", "connection", "start", "stop"]
            },
            "medium": {
                "question": "How does the Session Layer handle checkpoints and synchronization during long file transfers?",
                "hint": "It places checkpoints in the data stream so if the connection drops, transmission resumes from the last checkpoint instead of restarting from scratch.",
                "keywords": ["checkpoint", "synchroniz", "resume", "restart", "transfer", "drop", "session"]
            },
            "hard": {
                "question": "In remote procedure calls (RPC) and distributed transactions, how does Layer 5 session management coordinate two-phase commits (2PC) and session token revocation?",
                "hint": "It tracks transaction coordinators and participants across prepare/commit phases and ensures idempotent replay protection if sessions disconnect mid-transaction.",
                "keywords": ["rpc", "two-phase commit", "2pc", "idempotent", "token", "coordinator", "session state"]
            }
        },
        {
            "easy": {
                "question": "What does Layer 6 (Presentation Layer) do with data before handing it to the user?",
                "hint": "It formats, compresses, and encrypts or decrypts data (e.g. SSL/TLS, JPEG, ASCII).",
                "keywords": ["presentation", "format", "compress", "encrypt", "decrypt", "syntax", "ssl", "tls"]
            },
            "medium": {
                "question": "Why is character encoding (like ASCII vs UTF-8) a Presentation Layer responsibility?",
                "hint": "It ensures that text formatted on one operating system or language is properly translated into readable characters on another system.",
                "keywords": ["utf-8", "ascii", "encoding", "translat", "format", "character", "syntax"]
            },
            "hard": {
                "question": "Walk through the TLS 1.3 handshake at the Presentation Layer and contrast its 1-RTT key exchange (Diffie-Hellman ephemeral) with TLS 1.2's 2-RTT handshake.",
                "hint": "TLS 1.3 combines cipher proposal and ECDHE key share into the ClientHello, eliminating a round trip and mandating forward secrecy by removing static RSA key exchanges.",
                "keywords": ["tls 1.3", "handshake", "1-rtt", "ecdhe", "diffie-hellman", "forward secrecy", "clienthello", "rsa"]
            }
        },
        {
            "easy": {
                "question": "Which layer is Layer 7, and what are two common protocols you use on it?",
                "hint": "The Application Layer (e.g., HTTP, HTTPS, DNS, SMTP).",
                "keywords": ["application", "layer 7", "http", "https", "dns", "smtp", "ftp"]
            },
            "medium": {
                "question": "How does DNS (Domain Name System) function at Layer 7 to translate website names into IP addresses?",
                "hint": "When you type a domain like google.com, DNS queries root, TLD, and authoritative name servers to resolve it into an IP address.",
                "keywords": ["dns", "domain", "ip", "resolve", "query", "authoritative", "translate", "name"]
            },
            "hard": {
                "question": "Contrast HTTP/1.1 (pipelining with head-of-line blocking), HTTP/2 (binary framing with single TCP multiplexing), and HTTP/3 (QUIC over UDP) regarding transport-level head-of-line blocking.",
                "hint": "HTTP/2 multiplexes streams over one TCP connection, but TCP packet loss blocks all streams; HTTP/3 uses QUIC over UDP so packet loss on one stream does not stall independent streams.",
                "keywords": ["http/1.1", "http/2", "http/3", "quic", "head-of-line blocking", "multiplex", "udp", "binary framing"]
            }
        },
        {
            "easy": {
                "question": "What is 'data encapsulation' as an email message moves down the OSI model from Layer 7 to Layer 1?",
                "hint": "Each layer wraps its own header around the message like putting an envelope inside another envelope.",
                "keywords": ["encapsulat", "wrap", "header", "envelope", "down", "layer", "add"]
            },
            "medium": {
                "question": "Name the specific Protocol Data Unit (PDU) at Layer 4, Layer 3, and Layer 2.",
                "hint": "Layer 4 = Segment, Layer 3 = Packet, Layer 2 = Frame.",
                "keywords": ["segment", "packet", "frame", "pdu", "layer 4", "layer 3", "layer 2"]
            },
            "hard": {
                "question": "Trace a complete packet traversal from host A to host B through two routers: how do MAC addresses change at each hop while IP addresses remain constant?",
                "hint": "At each router hop, Layer 2 frames are stripped and rebuilt with the router's egress MAC as source and next-hop router's MAC as destination; Layer 3 IP headers remain unchanged (unless NATed) with decremented TTL.",
                "keywords": ["hop", "mac address", "change", "frame", "strip", "router", "ttl", "ip unchanged", "egress", "ingress"]
            }
        },
        {
            "easy": {
                "question": "Why is the OSI model still taught today if the modern internet actually runs on TCP/IP?",
                "hint": "Because it gives engineers a clear, universal framework to troubleshoot networking problems step-by-step.",
                "keywords": ["troubleshoot", "framework", "universal", "teach", "understand", "standard", "step-by-step"]
            },
            "medium": {
                "question": "How do network engineers use the 'divide-and-conquer' or 'bottom-up' troubleshooting methodology using the OSI layers?",
                "hint": "They start by checking physical cables (Layer 1), then link lights and MAC tables (Layer 2), IP pinging (Layer 3), and finally port access (Layer 4).",
                "keywords": ["bottom-up", "troubleshoot", "cable", "ping", "layer 1", "layer 3", "divide and conquer"]
            },
            "hard": {
                "question": "Explain how modern Software-Defined Networking (SDN) and OpenFlow decouple the Layer 3 Control Plane from the Data/Forwarding Plane to enable centralized network programmability.",
                "hint": "Traditional routers run distributed routing protocols and packet forwarding on the same box; SDN moves the control plane intelligence to a centralized controller, pushing flow rules to dumb switches via OpenFlow.",
                "keywords": ["sdn", "control plane", "data plane", "forwarding", "openflow", "controller", "programmab", "decouple"]
            }
        }
    ]
}

def resolve_concept_key(concept: str) -> str:
    c = concept.strip().lower()
    if "unsupervised" in c:
        return "unsupervised learning"
    if "supervised" in c:
        return "supervised learning"
    if "osi" in c:
        return "osi"
    if "cloud" in c or "iaas" in c or "paas" in c or "saas" in c:
        return "cloud computing"
    return "custom"

def call_ollama(prompt: str, timeout: int = 15) -> str:
    try:
        resp = requests.post(
            OLLAMA_API_URL,
            json={"model": DEFAULT_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama call skipped/failed: {e}")
    return ""

def get_question_item(concept: str, q_num: int, difficulty: int) -> dict:
    key = resolve_concept_key(concept)
    idx = max(0, min(9, q_num - 1))
    
    # Map integer difficulty 1, 2, 3 to tier
    diff_tier = "easy" if difficulty <= 1 else ("medium" if difficulty == 2 else "hard")
    
    if key in CURRICULUM_PLANS and idx < len(CURRICULUM_PLANS[key]):
        tier_data = CURRICULUM_PLANS[key][idx].get(diff_tier) or CURRICULUM_PLANS[key][idx]["easy"]
        return {
            "question": f"Question {q_num} of 10 ({diff_tier.capitalize()}): {tier_data['question']}",
            "hint": tier_data["hint"],
            "keywords": tier_data["keywords"]
        }

    # Custom topic dynamic generation with explicit difficulty styling
    diff_instruction = {
        "easy": "Create a simple, foundational question focusing on basic definitions or everyday analogies.",
        "medium": "Create an intermediate question focusing on operational mechanisms, comparisons, or practical trade-offs.",
        "hard": "Create an advanced, technical question focusing on deep architecture, edge-case troubleshooting, or mathematical nuances."
    }.get(diff_tier, "Create a clear guiding question.")

    prompt = (
        f"You are a Socratic tutor. Create Question {q_num} of 10 for the topic '{concept}'.\n"
        f"Difficulty: {diff_tier.upper()} ({difficulty}/3). {diff_instruction}\n"
        f"Return EXACTLY in this format:\n"
        f"QUESTION: <one clear guiding question under 25 words>\n"
        f"HINT: <one helpful hint under 20 words>"
    )
    raw = call_ollama(prompt, timeout=12)
    q_str = f"Question {q_num} of 10 ({diff_tier.capitalize()}): In your words, what is a key concept of {concept}?"
    h_str = "Think of its main architectural components and operational benefits."
    
    if "QUESTION:" in raw:
        try:
            parts = raw.split("HINT:")
            q_part = parts[0].replace("QUESTION:", "").strip()
            if q_part:
                q_str = f"Question {q_num} of 10 ({diff_tier.capitalize()}): {q_part}"
            if len(parts) > 1 and parts[1].strip():
                h_str = parts[1].strip()
        except Exception:
            pass

    return {
        "question": q_str,
        "hint": h_str,
        "keywords": [w.lower() for w in concept.split() if len(w) > 3]
    }

def evaluate_student_answer(answer: str, question_info: dict, concept: str) -> tuple[int, str]:
    cleaned = answer.strip().lower()
    
    # 1. Non-answers, conversational greetings, and short evasions
    invalid_tokens = ["no", "idk", "i don't know", "hello", "hi", "hey", "where", "what", "skip", "pass", "help", "nothing", "start"]
    if len(cleaned) < 2 or cleaned in invalid_tokens:
        return 0, f"That doesn't address the question. Key concept: {question_info['hint']}"
    if len(cleaned.split()) <= 2 and any(t == cleaned for t in invalid_tokens):
        return 0, f"Please provide a substantive answer. Consider: {question_info['hint']}"

    # 2. Keyword check
    keywords = question_info.get("keywords", [])
    matches = [k for k in keywords if k in cleaned]
    if len(matches) >= 1:
        return 10, f"Excellent! You accurately identified key elements: {', '.join(matches[:2])}."

    # 3. Thoughtful multi-word explanation
    if len(cleaned.split()) >= 4:
        return 10, f"Good explanation! Your reasoning aligns well with the concept."

    return 0, f"Not quite complete. Keep this hint in mind: {question_info['hint']}"

def generate_socratic_turn(student_id: str, concept: str, student_answer: str, history: list, difficulty: int, student_name: str, mode: str, question_num: int):
    # MODE 1: Direct Q&A
    if mode == "ask_tutor":
        prompt = (
            f"You are an encouraging Socratic tutor. The student is asking: '{student_answer}' regarding '{concept}'. "
            f"Provide a clear, helpful, direct explanation with a concrete example. Do not quiz the student or ask test questions."
        )
        reply = call_ollama(prompt, timeout=15)
        if not reply:
            reply = f"{concept} is an essential domain in computer science. For your question on '{student_answer}', remember that it structures how systems exchange data and execute logic."
        return {"feedback": reply, "score_delta": 0, "mastery_score": 0}

    # MODE 2: Guiding Questions (10-Question Test)
    q_num = question_num or 1
    
    # Starting the test
    if student_answer.strip().lower() == "start" or (q_num == 1 and not history):
        first_q = get_question_item(concept, 1, difficulty)
        return {
            "feedback": f"Welcome, {student_name}! Let's start Question 1 of 10.",
            "next_question": first_q["question"],
            "hint": first_q["hint"],
            "score_delta": 0,
            "mastery_score": 0
        }

    # Evaluate current answer
    current_q_info = get_question_item(concept, q_num, difficulty)
    score_delta, feedback_str = evaluate_student_answer(student_answer, current_q_info, concept)

    # Deliver next question
    if q_num < 10:
        next_q_info = get_question_item(concept, q_num + 1, difficulty)
        next_q_str = next_q_info["question"]
        hint_str = next_q_info["hint"]
    else:
        next_q_str = "You have completed all 10 questions of this evaluation!"
        hint_str = "Check your total mastery score above or view the Teacher Dashboard!"

    return {
        "feedback": feedback_str,
        "next_question": next_q_str,
        "hint": hint_str,
        "score_delta": score_delta
    }
