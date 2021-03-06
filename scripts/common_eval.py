# Common evaluation routines, including pure-Python computation of NDCG & MAP
import collections
import numpy as np
import subprocess
import math
from tqdm import tqdm

FAKE_RUN_ID = "fake_run"

METRIC_MAP = 'map'
# We hardcode 20, b/c it's hardcoded in gdeval.pl
NDCG_TOP_K = 20
METRIC_NDCG20 = 'ndcg@20'

METRIC_LIST = [METRIC_MAP, METRIC_NDCG20]

QrelEntry = collections.namedtuple('QrelEntry',
                                   'queryId docId relGrade')

RELEVANCE_THRESHOLD = 1e-5

qrelCache = {}

class NormalizedDiscountedCumulativeGain:
    def __init__(self, k):
        self._k = k

    def _dcg(self, relsSortedByScores):

        res = 0
        for i, rel in enumerate(relsSortedByScores):
            if i >= self._k:
                break
            if rel > RELEVANCE_THRESHOLD:
                res += (math.pow(2., rel) - 1.) / math.log(2. + i)

        return res

    def __call__(self, relsSortedByScores, qrelDict):
        """
        Calculate NDCG. The function assumes,
        we already sorted everything in the order of decreasing scores.

        :param relsSortedByScores: true relevance judgements sorted by scores.
        :param qrelDict: true relevance scores indexed by document ids
        :return: NDCG.
        """
        idcg = self._dcg(sorted(qrelDict.values(), reverse=True))
        return self._dcg(relsSortedByScores) / idcg if idcg > 0 else 0


class MeanAveragePrecision:
    def __call__(self, relsSortedByScores, qrelDict):
        """
        Calculate mean average precision. The function assumes,
        we already sorted everything in the order of decreasing scores.

        :param relsSortedByScores: true relevance judgements sorted by scores.
        :param qrelDict: true relevance scores indexed by document ids
        :return: Mean average precision.
        """
        result = 0.
        postQty = len(qrelDict)

        pos = 0
        for i, rel in enumerate(relsSortedByScores):
            if rel > RELEVANCE_THRESHOLD:
                pos += 1.
                result += pos / (i + 1.)

        return result / postQty


def genQrelStr(queryId, docId, relGrade):
    """Produces a string representing one QREL entry

    :param queryId:   question/query ID
    :param docId:     relevanet document/answer ID
    :param relGrade:  relevance grade

    :return: a string representing one QREL entry
    """
    return f'{queryId} 0 {docId} {relGrade}'


def qrelEntry2Str(qrelEntry):
    """Convert a parsed QREL entry to string.

    :param qrelEntry: input of the type QrelEntry
    :return:  string representation.
    """
    return genQrelStr(qrelEntry.queryId, qrelEntry.docId, qrelEntry.relGrade)


def parseQrelEntry(line):
    """Parse one QREL entry
    :param line  a single line with a QREL entry.
            Relevance graded is expected to be integer.

    :return a parsed QrelEntry entry.
    """

    line = line.strip()
    parts = line.split()
    if len(parts) != 4:
        raise Exception('QREL entry format error, expecting just 4 white-space separted field in the entry: ' + line)

    return QrelEntry(queryId=parts[0], docId=parts[2], relGrade=int(parts[3]))


def readQrels(fileName):
    """Read and parse QRELs.

    :param fileName: input file name
    :return: an array of parsed QREL entries
    """
    ln = 0
    res = []

    with open(fileName) as f:
        for line in tqdm(f, desc='loading qrels (by line)', leave=False):
            ln += 1
            line = line.strip()
            if not line:
                continue
            try:
                e = parseQrelEntry(line)
                res.append(e)
            except:
                raise Exception('Error parsing QRELs in line: %d' % ln)

    return res


def getSorteScoresFromScoreDict(queryRunDict):
    """Take a dictionary of document scores indexed by the document id
    and produce a list of (document id, score tuples) sorted
    in the order of decreasing scores.

    :param   queryRunDict: a single-query run info in the dictionary format.
    """
    return list(sorted(queryRunDict.items(), key=lambda x: (x[1], x[0]), reverse=True))


def writeRunDict(runDict, fileName):
    """Write a dictionary-stored run to a file. The input
       is actually a dictionary of dictinoary. The outer
       dictionary is a set of query-specific results
       indexed by the query id. And the internal dictionary
       is a set of document scores indexed by the document id.
       Before writing data, it is resorted within each query.

    :param runDict:    a run dictionary
    :param fileName:  an output file name
    """
    with open(fileName, 'wt') as runfile:
        for qid in runDict:
            scores = getSorteScoresFromScoreDict(runDict[qid])
            for i, (did, score) in enumerate(scores):
                runfile.write(genRunEntryStr(qid, did, i + 1, score, FAKE_RUN_ID) + '\n')


def writeQrels(qrelList, fileName):
    """Write a list of QRELs to a file.

    :param qrelList:  a list of parsed QRELs
    :param fileName:  an output file name
    """
    with open(fileName, 'w') as f:
        for e in qrelList:
            f.write(qrelEntry2Str(e))
            f.write('\n')


def genRunEntryStr(queryId, docId, rank, score, runId):
    """A simple function to generate one run entry.

    :param queryId: query id
    :param docId:   document id
    :param rank:    entry rank
    :param score:   entry score
    :param runId:   run id

    """
    return f'{queryId} Q0 {docId} {rank} {score} {runId}'


def readQrelsDict(fileName):
    """Read QRELs in the form of a dictionary where keys are query IDs.

    :param fileName: QREL file name
    :return: a dictionary of dictionaries
    """
    result = {}
    for e in readQrels(fileName):
        result.setdefault(e.queryId, {})[e.docId] = int(e.relGrade)
    return result


def readRunDict(fileName):
    """Read a run file in the form of a dictionary where keys are query IDs.

    :param fileName: run file name
    :return:
    """
    result = {}
    with open(fileName) as f:
        for ln, line in enumerate(tqdm(f, desc='loading run (by line)', leave=False)):
            line = line.strip()
            if not line:
                continue
            fld = line.split()
            if len(fld) != 6:
                ln += 1
                raise Exception(
                    f'Invalid line {ln} in run file {fileName} expected 6 white-space separated fields by got: {line}')

            qid, _, docid, rank, score, _ = fld
            result.setdefault(qid, {})[docid] = float(score)

    return result


def evalRun(rerankRun, runFileName, qrelFileName, metricFunc,
            saveRun=False, debug=False, useQrelCache=False):
    """Evaluate run stored in a file using QRELs stored in a file.

    :param rerankRun:     a run dictionary (of dictionaries)
    :param runFileName:   a run file name (for external tools)
    :param qrelFileName:  a QREL file name
    :param metricFunc:    a metric function or class instance with overloaded __call__
    :param saveRun:       true if we want to save the run
    :return:  the average metric value
    """

    if saveRun:
        writeRunDict(rerankRun, runFileName)

    global qrelCache

    if useQrelCache and qrelFileName in qrelCache:
        qrels = qrelCache[qrelFileName]
    else:
        qrels = qrelCache[qrelFileName] = readQrelsDict(qrelFileName)

    resArr = []

    for qid, scoreDict in rerankRun.items():
        relsSortedByScores = []

        val = 0

        if qid in qrels:
            queryQrelDict = qrels[qid]

            for did, score in getSorteScoresFromScoreDict(scoreDict):
                rel_score = 0
                if did in queryQrelDict:
                    rel_score = queryQrelDict[did]

                relsSortedByScores.append(rel_score)

            val = metricFunc(relsSortedByScores, queryQrelDict) if queryQrelDict else 0

        if debug:
            print('%s %g' % (qid, val))

        resArr.append(val)

    res = np.mean(resArr)
    if debug:
        print('mean %g' % res)

    return res


def getEvalResults(useExternalEval, evalMetric,
                   rerankRun, runFile, qrelFile,
                   useQrelCache=False):
    """Carry out internal or external evaluation.

    :param useExternalEval:   True to use external evaluation tools.
    :param evalMetric:        Evaluation metric (from the METRIC_LIST above)
    :param runFile:           A run file to store results for external eval tool.
    :param qrelFile:          A QREL file.
    :return:  average metric value.
    """

    if useExternalEval:
        m = None
        if evalMetric == METRIC_MAP:
            m = 'map'
        elif evalMetric == METRIC_NDCG20:
            m = 'ndcg_cut_20'
        else:
            raise Exception('Unsupported metric: ' + evalMetric)

        return trec_eval(runFile, qrelFile, m)
    else:
        f = None
        if evalMetric == METRIC_MAP:
            f = MeanAveragePrecision()
        elif evalMetric == METRIC_NDCG20:
            f = NormalizedDiscountedCumulativeGain(NDCG_TOP_K)
        else:
            raise Exception('Unsupported metric: ' + evalMetric)

        return evalRun(rerankRun, runFile, qrelFile, f, useQrelCache=useQrelCache)


def trec_eval(runf, qrelf, metric):
    trec_eval_f = 'trec_eval/trec_eval'
    trec_eval_params = [trec_eval_f,
                        '-m', 'official',
                        '-m', 'ndcg_cut',
                        qrelf, runf]
    # print(' '.join(trec_eval_params))
    for line in subprocess.check_output(trec_eval_params).decode().split('\n'):
        fields = line.rstrip().split()
        if len(fields) == 3 and fields[0] == metric:
            return float(fields[2])

    raise Exception(
        f'Cannot get the value of the metric {metric} by evaluating file {runf} with qrels {qrelf}')
