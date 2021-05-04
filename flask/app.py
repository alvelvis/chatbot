from flask import Flask, render_template, jsonify, request
import os
import sys
import shutil
import re
import json
import urllib
import estrutura_ud
import interrogar_UD
import numpy as np
from gensim.test.utils import datapath, get_tmpfile
from gensim.models import Word2Vec
import pprint
import unidecode
import random
import wikipedia
from bs4 import BeautifulSoup
wikipedia.set_lang("pt")

app = Flask(__name__)

def remove_accents(word):
    return unidecode.unidecode(word)

model = Word2Vec.load("publico-COMPLETO-100.txt.model")
hybrid = model.wv

contrast_corpus = "bosque-ud-2.6.conllu"
with open(contrast_corpus) as f:
    contrast_corpus = list(map(lambda y: y.split("\t")[2].lower(), list(filter(lambda x: len(x.split("\t")) == 10 and x.split("\t")[3] in ["NOUN", "VERB", "PROPN"], f.read().splitlines()))))
frequency_of_important_words = {x: contrast_corpus.count(x) for x in set(contrast_corpus)}

linguistic_patterns = {
    'functions': [
        [
            {
                'lemma': 'você|tu|qual|quais',
                'deprel': 'nsubj',
                'head_token.lemma': 'fazer|realizar|função',
            }
        ],
        [
        
            {
                'lemma': 'você|tu|qual|quais',
                'deprel': 'nsubj',
            },
            {
                'lemma': 'fazer|realizar|função',
                'deprel': 'xcomp',
            }
        ]
    ]
}

# EXTEND LINGUISTIC PATTERNS WITH SIMILAR WORDS
for resp, pattern in linguistic_patterns.items():
    for q, query in enumerate(pattern):
        for e, exp in enumerate(query):
            expression = []
            for col in exp:
                if 'lemma' in col:
                    linguistic_patterns[resp][q][e][col] = remove_accents(linguistic_patterns[resp][q][e][col]).split("|")
                    if any(x in hybrid.key_to_index for x in linguistic_patterns[resp][q][e][col]):
                        linguistic_patterns[resp][q][e][col].extend(list(map(lambda x: x[0], hybrid.most_similar(positive=list(filter(lambda x: x in hybrid.key_to_index, linguistic_patterns[resp][q][e][col])), topn=10))))
                    linguistic_patterns[resp][q][e][col] = "|".join(list(set(linguistic_patterns[resp][q][e][col])))
                expression.append('{} = "{}"'.format(col, linguistic_patterns[resp][q][e][col]))
            linguistic_patterns[resp][q][e] = " and ".join(expression)  
print(json.dumps(linguistic_patterns, indent=4, ensure_ascii=False))

responses = {
    'functions': "Ainda não tenho uma lista de funcionalidades, me desculpe...",
}

app_dict = {
    'keywords': [
        ("tudo o que eu faço", "O que você pode fazer?")
    ],
}

@app.route('/', methods=["POST"])
def api():
    api_response = ""
    bot_response = ""    
   
    # PARSE THE USER INPUT AND LOOK FOR PATTERNS
    if request.form.get('api_response'):
        api_response = app_dict[request.form.get('api_response')]
    if request.form.get('input'):
        udpipe_url = "http://lindat.mff.cuni.cz/services/udpipe/api/process?tokenizer&tagger&parser"
        udpipe_data = urllib.parse.urlencode({
            'data': request.form.get('input'),
            'model': "portuguese-bosque-ud-2.6-200830",
            }).encode('ascii')
        with urllib.request.urlopen(udpipe_url, udpipe_data) as f:
            udpipe_output = json.loads(remove_accents(f.read().decode('utf-8')))['result']
            text = estrutura_ud.Corpus(recursivo=True)
            text.build(udpipe_output)
        print("input: {}".format(text.to_str()))

        # try to find linguistic pattern   
        for pattern in linguistic_patterns:
            for query in linguistic_patterns[pattern]:
                #print(query)
                if all(interrogar_UD.main(text, 5, x, fastSearch=True)['casos'] for x in query):
                    bot_response = responses[pattern]
                    break
        
        # try to answer from wikipedia
        if not bot_response:
            # get most awkward word in input
            names = []
            verbs = []
            for sentence in text.sentences.values():
                for token in sentence.tokens:
                    clean_token = token.lemma.lower()
                    if token.upos in ["NOUN", "PROPN"] and not clean_token in names and clean_token in frequency_of_important_words:
                        names.append(clean_token)
                    if (token.upos in ["VERB"] or token.deprel in ["cop"]) and not clean_token in verbs and clean_token in frequency_of_important_words:
                        verbs.append(clean_token)
            most_awkward_name = sorted(names, key=lambda x: frequency_of_important_words[x])
            most_awkward_verb = sorted(verbs, key=lambda x: frequency_of_important_words[x])
            if most_awkward_name:
                try:
                    bot_response = wikipedia.summary(most_awkward_name[0], sentences=2)
                except wikipedia.DisambiguationError as e:
                    s = random.choice(e.options)
                    bot_response = wikipedia.summary(s, sentences=2)
        
        # try to answer from "pensador"
        if not bot_response and most_awkward_verb:
            with urllib.request.urlopen("https://www.pensador.com/{}/".format(most_awkward_verb[0])) as f:
                soup = BeautifulSoup(f, "html.parser")
                parse = soup.find_all("p", class_="frase")
                bot_response = random.choice(parse).get_text() if parse else ""
        
        # no answer found
        if not bot_response:
            bot_response = "Desculpe, ainda não sei como responder..."

    response = jsonify({"api_response": api_response, "bot_response": bot_response})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    app.run(debug=True)
