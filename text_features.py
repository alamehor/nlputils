from __future__ import division
import re
from collections import Counter
from math import log
from unidecode import unidecode
from misc import norm_dict, invert_dict2, select_copy

def extract_features(text, norm='max', allnum=True):
    """
    Input:
        text: some text for which features should be computed
        norm (either None, 'max', 'nwords', or 'length'): how to normalize the counts
        allnum (bool): how to deal with numbers - if True, all numbers will be taken as features like words,
                       otherwise only a feature __NUMBER will be 0 or 1
    Output:
        a dictionary with (possibly normalized) counts of the occurrences or words or n-grams in the text
    """
    # clean the text: no fucked up characters, html, ...
    text = unidecode(text.decode("utf-8"))
    text = re.sub(r"http(s)?://\S*", " ", text) # remove links
    text = text.lower()
    # extract feature dict
    num = 0
    if allnum:
        wordregex = r'[A-Za-z0-9]+'
    else:
        wordregex = r'[A-Za-z]+'
        if re.search(r"[0-9]+",text):
            num = 1 #len(re.findall(r"[0-9]+",text))
    featdict = dict(Counter(re.findall(wordregex,text)))
    if num:
        featdict['__NUMBER'] = min(num,max(featdict.values()))
    # possibly normalize
    if norm:
        featdict = norm_dict(featdict, norm=norm)
    return featdict

def _length(docfeats):
    """
    docfeats: a dict with doc_id:{term:count}
    """
    # invert the dictionary to be term:{doc_id:count}, all we need are the terms though
    termlist = set(invert_dict2(docfeats).keys())
    # compute number of characters for every term
    return norm_dict({term:len(term) for term in termlist})

def _df(docfeats):
    """
    docfeats: a dict with doc_id:{term:count}
    """
    # total number of documents
    N = float(len(docfeats))
    # invert the dictionary to be term:{doc_id:count}
    termdocs = invert_dict2(docfeats)
    # compute df for every term
    return norm_dict({term:1.-len(termdocs[term])/N for term in termdocs})

def _idf(docfeats):
    """
    docfeats: a dict with doc_id:{term:count}
    """
    # total number of documents
    N = float(len(docfeats))
    # invert the dictionary to be term:{doc_id:count}
    termdocs = invert_dict2(docfeats)
    # compute idf for every term
    return norm_dict({term:log(N/len(termdocs[term])) for term in termdocs})

def _pidf(docfeats):
    """
    docfeats: a dict with doc_id:{term:count}
    """
    # total number of documents
    N = float(len(docfeats))
    # invert the dictionary to be term:{doc_id:count}
    termdocs = invert_dict2(docfeats)
    # compute idf for every term
    return norm_dict({term:max(0.,log((N-len(termdocs[term]+1.))/len(termdocs[term]))) for term in termdocs})


def getall_features(textdict, norm='max', allnum=True, weight='idf', renorm='max', w_ids=[]):
    """
    extracts (and normalizes) features, applies term weights and renormalizes features for a whole dict of docs
    Input:
        textdict: dict with doc_id:text
        norm (binary, max, length, nwords, None): how the term counts for each doc should be normalized
        allnum (True or False): if numbers should be considered
        weight: possible term weights to be applied (if 'idf', etc. weights will be computed)
                can also be a dict for precomputed weights, then they will be directly applied 
        renorm: how the features with applied weights should be renormalized
        w_ids: if only a portion of all texts should be used to compute the weights (e.g. only training data)
    Returns:
        docfeats: dict with doc_id:{feature:count} (where the features depend on the parameters)
    """
    # extract all word features and possibly normalize them
    docfeats = {}
    print "extracting features"
    for doc, text in textdict.iteritems():
        docfeats[doc] = extract_features(text, norm, allnum)
    # possibly compute weights
    if not w_ids:
        w_ids = docfeats.keys()
    if type(weight) == dict:
        Dw = weight
    elif weight == 'length':
        print "computing length weights"
        Dw = _length(select_copy(docfeats, w_ids))
    elif weight == 'df':
        print "computing df weights"
        Dw = _df(select_copy(docfeats, w_ids))
    elif weight == 'idf':
        print "computing idf weights"
        Dw = _idf(select_copy(docfeats, w_ids))
    elif weight == 'pidf':
        print "computing pidf weights"
        Dw = _pidf(select_copy(docfeats, w_ids))
    else:
        Dw = {}
    # possibly apply weights and renormalize
    if Dw:
        print "applying weights"
        for doc in docfeats:
            # if the word was not in Dw (= not in the training set), delete it (otherwise it can mess with renormalization)
            docfeats[doc] = {term:docfeats[doc][term]*Dw[term] for term in docfeats[doc] if term in Dw}
            if renorm:
                docfeats[doc] = norm_dict(docfeats[doc],norm=renorm)
    return docfeats