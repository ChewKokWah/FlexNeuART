package edu.cmu.lti.oaqa.flexneuart.simil_func;

import java.util.*;

import edu.cmu.lti.oaqa.flexneuart.fwdindx.DocEntryParsed;
import edu.cmu.lti.oaqa.flexneuart.fwdindx.ForwardIndex;
import edu.cmu.lti.oaqa.flexneuart.fwdindx.WordEntry;

/**
 * A re-implementation of the default Lucene/SOLR BM25 similarity. 
 *
 * <p>Unlike the original implementation, though, we don't rely on a coarse
 * version of the document normalization factor. 
 * Our approach is easier to implement.</p>
 * 
 * @author Leonid Boytsov
 *
 */
public class DefaultSimilarityLucene extends TFIDFSimilarity {
  public DefaultSimilarityLucene(ForwardIndex fieldIndex) {
    mFieldIndex = fieldIndex;
  }
  
  @Override
  protected float computeIDF(float docQty, WordEntry e) {
    float n = e.mWordFreq;
    return (float)(Math.log(docQty/(double)(n + 1)) + 1.0);
  }

  final ForwardIndex mFieldIndex;
  
  
  /**
   * Computes the similarity between the query (represented by
   * a DocEntry object) and the document (also represented by a DocEntry object)
   * 
   * @param query
   * @param document
   * @return
   */
  @Override
  public float compute(DocEntryParsed query, DocEntryParsed doc) {
    float score = 0;
    
    int   docTermQty = doc.mWordIds.length;
    int   queryTermQty = query.mWordIds.length;
    
    int   iQuery = 0, iDoc = 0;
    
    float docLen = doc.mDocLen;
    
//    float queryNorm = 0;
    float lengthNorm = docLen > 0 ? ((float) (1.0 / Math.sqrt(docLen))) : 0;
    
    while (iQuery < queryTermQty && iDoc < docTermQty) {
      final int queryWordId = query.mWordIds[iQuery];
      final int docWordId   = doc.mWordIds[iDoc];
      
      if (queryWordId < docWordId) ++iQuery;
      else if (queryWordId > docWordId) ++iDoc;
      else {
        float tf = (float)Math.sqrt(doc.mQtys[iDoc]);
        
        float idf = getIDF(mFieldIndex, query.mWordIds[iQuery]);
        float idfSquared = idf * idf;
        
//        System.out.println(String.format("## Word %s sqrt(tf)=%f idf=%f", 
//                                        mFieldIndex.getWord(query.mWordIds[iQuery]), tf, idf));
        
// Contrary to what docs say: It looks like Lucene actually doesn't use this query normalizer        
//        queryNorm += idfSquared;
        
        score +=  query.mQtys[iQuery] *           // query frequency
                  tf * idfSquared;
        
        ++iQuery; ++iDoc;
      }
    }
    
//    queryNorm = (float)Math.sqrt(queryNorm);
    
//    System.out.println(String.format("## queryNorm=%f lengthNorm=%f", queryNorm, lengthNorm));
    
    score *= lengthNorm;
    
// Contrary to what the docs say: It looks like Lucene actually doesn't use this query normalizer    
//    if (queryNorm > 0)
//      score /= queryNorm;
            
    return score;
  }

  @Override
  public String getName() {
    return "Default";
  }
}
