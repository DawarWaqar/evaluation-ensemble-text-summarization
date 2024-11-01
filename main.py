import re
import pandas as pd
import nltk
import ssl
import numpy as np


from textacy import preprocessing as prep
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from rouge import Rouge
from nltk.tokenize.punkt import PunktSentenceTokenizer
from scipy import stats

# from matplotlib import pyplot as plt

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download("punkt")
nltk.download("stopwords")


def replace_dots(text):
    text = re.sub(r"(?<!\d)\.{1,}(?!\d)", ". ", text)
    return re.sub(r"(?<=\d)\.(?=[^\d]|$)", ". ", text)


def preprocess_text(df):
    # the preprocessing pipeline
    process = prep.make_pipeline(
        prep.replace.emojis,
        prep.replace.emails,
        prep.replace.urls,
        prep.replace.phone_numbers,
        prep.remove.html_tags,
        prep.normalize.hyphenated_words,
        prep.normalize.whitespace,
        prep.normalize.unicode,
        prep.normalize.quotation_marks,
        prep.normalize.bullet_points,
    )

    # apply the pre-processing pipeline on the dataframe
    df.text = df.text.apply(process)
    df.summary = df.summary.apply(process)
    # return the dataframe
    return df


def summarizer(text, num_sentences=3, sum_custom=LsaSummarizer):
    # tokenizer
    tokenizer = Tokenizer(language="english")
    # parser
    parser = PlaintextParser.from_string(text, tokenizer)
    # summarizer
    summarizerInstance = sum_custom()
    summary = summarizerInstance(parser.document, num_sentences)

    # join sentences to form a summary
    summary = " ".join([str(sent) for sent in summary])
    return summary


def calc_rouge(df, col1, col2):
    rouge = Rouge()
    # calculate rogue scores
    r_scores = rouge.get_scores(df[col1], df[col2])
    df_result = pd.DataFrame(r_scores)
    return df_result


def avg_rouge(df, col1, col2, col3):
    avg_r1 = 0
    avg_r2 = 0
    avg_rL = 0
    n = df.shape[0]
    for i in range(n):
        avg_r1 += df[col1].iloc[i]["r"]
        avg_r2 += df[col2].iloc[i]["r"]
        avg_rL += df[col3].iloc[i]["r"]

    avg_r1 = avg_r1 / n
    avg_r2 = avg_r2 / n
    avg_rL = avg_rL / n

    # return the average rouge scores
    return avg_r1, avg_r2, avg_rL


def isSentenceInParagraph(sentence, paragraph):
    list_of_sentences = paragraph.split(".")
    if sentence in paragraph:
        return 1
    return 0


def generate_ensemble_summary(
    row, lsa_weight, lexrank_weight, luhn_weight, sum_basic_weight
):
    text_score_dict = {}
    tokenizer = PunktSentenceTokenizer()
    list_of_sentences_text = tokenizer.tokenize(row["text"])

    for sentence in list_of_sentences_text:

        text_score_dict[sentence] = (
            (isSentenceInParagraph(sentence, row["lsa_summary"]) * lsa_weight)
            + (isSentenceInParagraph(sentence, row["lexrank_summary"]) * lexrank_weight)
            + (isSentenceInParagraph(sentence, row["luhn_summary"]) * luhn_weight)
            + (
                isSentenceInParagraph(sentence, row["sum_basic_summary"])
                * sum_basic_weight
            )
        )

    # sort text_score_dict in descending order of scores
    sorted_text_score_dict = dict(
        sorted(text_score_dict.items(), key=lambda item: item[1], reverse=True)
    )

    return ".".join(list(sorted_text_score_dict.keys())[:3])


def perform_t_test(scores_1, scores_2):
    # calculate pairwise differences
    differences = scores_1 - scores_2

    t_statistic, p_value = stats.ttest_rel(scores_1, scores_2)

    print("Paired Samples T-test Results:")
    print("t-statistic:", t_statistic)
    print("p-value:", p_value)
    # Interpret the results
    alpha = 0.05
    if p_value < alpha:
        print(
            "Reject the null hypothesis. There is a significant difference between the mean ROUGE scores of Model 1 and Model 2."
        )
    else:
        print(
            "Fail to reject the null hypothesis. There is no significant difference between the mean ROUGE scores of Model 1 and Model 2."
        )


def return_scores(df, column):
    val = []
    for idx in range(df.shape[0]):
        val.append(df[column].iloc[idx]["r"])

    return np.array(val)
