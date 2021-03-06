package edu.cmu.lti.oaqa.flexneuart.letor;

import java.util.ArrayList;
import java.util.Map;

import edu.cmu.lti.oaqa.flexneuart.cand_providers.CandidateEntry;
import edu.cmu.lti.oaqa.flexneuart.fwdindx.DocEntryParsed;
import edu.cmu.lti.oaqa.flexneuart.utils.VectorWrapper;
import no.uib.cipr.matrix.DenseVector;

/**
 * A single-field, single-score feature generator,
 * whose score can be computed (exactly or approximately)
 * as an inner product between two vectors. Note, again,
 * that query and index fields can be different.
 * 
 * @author Leonid Boytsov
 *
 */
public abstract class SingleFieldInnerProdFeatExtractor extends SingleFieldFeatExtractor {

  public SingleFieldInnerProdFeatExtractor(FeatExtrResourceManager resMngr, OneFeatExtrConf conf) throws Exception {
    super(resMngr, conf);
  }

  /**
   * @return true if generates a sparse feature vector.
   */
  public abstract boolean isSparse();

  public abstract int getDim();
  
  @Override
  public abstract String getName();

  @Override
  public abstract Map<String, DenseVector> 
                  getFeatures(CandidateEntry cands[], Map<String, String> queryData) throws Exception;
  
  /**
   * This function produces a query and a document vector whose 
   * inner product is exactly or approximately equal to the only generated
   * feature value.
   * 
   * @param e a DocEntry object
   * 
   * @param isQuery true for queries and false for documents.
   * 
   * @return a possibly empty array of vector wrapper objects or null
   *         if the inner-product representation is not possible.
   * @throws Exception 
   */
  public abstract VectorWrapper getFeatInnerProdVector(DocEntryParsed e, boolean isQuery) throws Exception;

  public int getFeatureQty() {
    return 1;
  }

}
