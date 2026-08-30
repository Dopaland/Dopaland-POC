"""
D6 precision simulation -- a simple multinomial logistic regression, built
from scratch (numpy + scipy.optimize) because scikit-learn is not installed
in this environment and the task scope permits only "simple model families"
in any case (CLAUDE.md: "via the simple model families the client's scope
permits"). Standalone; does not import from features/.

Parameterization: a full (redundant) W (n_features x n_classes) + b
(n_classes,) softmax regression with L2 regularization. The redundancy
(softmax is invariant to adding a constant to every class's logit) is
resolved by the L2 penalty, which is standard practice and keeps the
implementation simple -- this is a documented simplification, not a claim
that the parameterization is minimal.
"""

import numpy as np
from scipy.optimize import minimize


def _softmax_rows(logits):
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def _unpack(theta, n_features, n_classes):
    w = theta[: n_features * n_classes].reshape(n_features, n_classes)
    b = theta[n_features * n_classes :]
    return w, b


def _neg_log_lik_and_grad(theta, X, y_onehot, n_features, n_classes, l2):
    w, b = _unpack(theta, n_features, n_classes)
    logits = X @ w + b
    probs = _softmax_rows(logits)
    n = X.shape[0]

    eps = 1e-12
    nll = -np.sum(y_onehot * np.log(probs + eps)) / n
    nll += 0.5 * l2 * np.sum(w ** 2) / n

    grad_logits = (probs - y_onehot) / n
    grad_w = X.T @ grad_logits + l2 * w / n
    grad_b = grad_logits.sum(axis=0)

    grad = np.concatenate([grad_w.ravel(), grad_b])
    return nll, grad


def fit_multinomial_logreg(X, y, n_classes, l2=1.0, max_iter=200):
    """X: (n_samples, n_features) float array (already including any bias/
    dummy columns the caller wants -- this function adds its own intercept
    term `b` separately, so X should NOT contain a constant column).
    y: (n_samples,) int array, values in [0, n_classes).

    Returns a dict {"w": (n_features, n_classes), "b": (n_classes,)}.
    """
    n_samples, n_features = X.shape
    y_onehot = np.zeros((n_samples, n_classes))
    y_onehot[np.arange(n_samples), y] = 1.0

    theta0 = np.zeros(n_features * n_classes + n_classes)
    result = minimize(
        _neg_log_lik_and_grad,
        theta0,
        args=(X, y_onehot, n_features, n_classes, l2),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": max_iter},
    )
    w, b = _unpack(result.x, n_features, n_classes)
    return {"w": w, "b": b, "converged": bool(result.success), "n_iter": int(result.nit)}


def predict_proba(params, X):
    logits = X @ params["w"] + params["b"]
    return _softmax_rows(logits)


def predict(params, X):
    return np.argmax(predict_proba(params, X), axis=1)


def macro_f1(y_true, y_pred, n_classes):
    """Unweighted mean of per-class F1. Standard macro-F1 -- no class
    weighting, so a class with few samples counts as much as a common one
    (this is what makes it the natural default for an imbalanced,
    drifting-frequency class distribution like A4's)."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    f1s = []
    for c in range(n_classes):
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))
