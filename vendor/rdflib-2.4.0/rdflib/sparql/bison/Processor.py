from rdflib import sparql
from rdflib.sparql.bison.Query import Query, Prolog
from rdflib.sparql.bison.SPARQLEvaluate import Evaluate        
from rdflib.sparql.bison import SPARQLParserc as SPARQLParser

def CreateSPARQLParser():
    return SPARQLParser.new()    

def Parse(query,debug = False):    
    p = CreateSPARQLParser()
    if debug:
        try:
           p.debug_mode(1)
        except:
            p.debug = 1    
    if not isinstance(query, unicode):
        query = unicode(query,'utf-8')
    return p.parse(query)

class Processor(sparql.Processor):

    def __init__(self, graph):
        self.graph = graph

    def query(self, strOrQuery, initBindings={}, initNs={}, DEBUG=False):
        assert isinstance(strOrQuery, (basestring, Query)), "%s must be a string or an rdflib.sparql.bison.Query.Query instance"%strOrQuery
        if isinstance(strOrQuery, basestring):
            strOrQuery = Parse(strOrQuery, DEBUG)
        if not strOrQuery.prolog:
                strOrQuery.prolog = Prolog(None, [])
                strOrQuery.prolog.prefixBindings.update(initNs)
        else:
            for prefix, nsInst in initNs.items():
                if prefix not in strOrQuery.prolog.prefixBindings:
                    strOrQuery.prolog.prefixBindings[prefix] = nsInst
        return  Evaluate(self.graph, strOrQuery, initBindings, DEBUG=DEBUG)
