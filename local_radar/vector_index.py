"""
Vector Index and RAG (Trailkeeper) for Local Radar
Provides semantic search, document embeddings, and change detection
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from .config import config
from .base import ReportEntry


class VectorIndex:
    """Vector embedding and semantic search functionality"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create index directory
        Path(self.config.vector.index_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        self.embedding_model = None
        self.faiss_index = None
        self.documents = []
        self.document_metadata = []
        
        # Fallback to TF-IDF if sentence-transformers not available
        self.use_sentence_transformers = SENTENCE_TRANSFORMERS_AVAILABLE and FAISS_AVAILABLE
        if not self.use_sentence_transformers:
            self.logger.warning("Using basic text matching fallback (advanced dependencies not available)")
            if SKLEARN_AVAILABLE:
                self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                self.tfidf_matrix = None
            else:
                self.tfidf_vectorizer = None
                self.tfidf_matrix = None
        
        # Download NLTK data if needed
        self._ensure_nltk_data()
        
        # Load existing index
        self._load_index()
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded"""
        if not NLTK_AVAILABLE:
            return
            
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
            except Exception as e:
                self.logger.warning(f"Could not download NLTK punkt: {e}")
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            try:
                nltk.download('stopwords', quiet=True)
            except Exception as e:
                self.logger.warning(f"Could not download NLTK stopwords: {e}")
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model"""
        if not self.use_sentence_transformers:
            return
        
        try:
            if self.embedding_model is None:
                self.logger.info(f"Loading embedding model: {self.config.vector.embedding_model}")
                self.embedding_model = SentenceTransformer(self.config.vector.embedding_model)
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            self.use_sentence_transformers = False
            self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add a document to the vector index"""
        if metadata is None:
            metadata = {}
        
        # Generate document ID
        doc_id = hashlib.md5(text.encode()).hexdigest()
        metadata['doc_id'] = doc_id
        metadata['added_at'] = datetime.now().isoformat()
        
        # Add to documents list
        self.documents.append(text)
        self.document_metadata.append(metadata)
        
        # Update index
        self._update_index()
        
        return doc_id
    
    def add_report_entry(self, entry: ReportEntry) -> str:
        """Add a report entry to the vector index"""
        metadata = {
            'title': entry.title,
            'source_url': entry.source_url,
            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
            'tags': entry.tags,
            'confidence_score': entry.confidence_score,
            'type': 'report_entry'
        }
        metadata.update(entry.metadata)
        
        # Combine title and content for indexing
        full_text = f"{entry.title}\n\n{entry.content}"
        
        return self.add_document(full_text, metadata)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search the vector index for similar documents"""
        if not self.documents:
            return []
        
        try:
            if self.use_sentence_transformers and self.embedding_model is not None:
                return self._search_with_embeddings(query, top_k)
            elif SKLEARN_AVAILABLE and self.tfidf_vectorizer is not None:
                return self._search_with_tfidf(query, top_k)
            else:
                return self._search_basic(query, top_k)
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def semantic_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """Compare two texts for semantic differences"""
        try:
            if self.use_sentence_transformers and self.embedding_model is not None:
                return self._semantic_diff_embeddings(text1, text2)
            else:
                return self._semantic_diff_tfidf(text1, text2)
        except Exception as e:
            self.logger.error(f"Semantic diff failed: {e}")
            return {
                'similarity_score': 0.0,
                'difference_score': 1.0,
                'method': 'error',
                'error': str(e)
            }
    
    def sentence_level_changes(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """Detect sentence-level changes between two texts"""
        try:
            # Tokenize into sentences
            if NLTK_AVAILABLE:
                old_sentences = sent_tokenize(old_text)
                new_sentences = sent_tokenize(new_text)
            else:
                # Basic sentence splitting fallback
                old_sentences = [s.strip() for s in old_text.split('.') if s.strip()]
                new_sentences = [s.strip() for s in new_text.split('.') if s.strip()]
            
            changes = []
            
            # Simple diff algorithm
            old_set = set(old_sentences)
            new_set = set(new_sentences)
            
            # Find deleted sentences
            for sentence in old_sentences:
                if sentence not in new_set:
                    changes.append({
                        'type': 'deleted',
                        'sentence': sentence,
                        'position': old_sentences.index(sentence)
                    })
            
            # Find added sentences
            for sentence in new_sentences:
                if sentence not in old_set:
                    changes.append({
                        'type': 'added',
                        'sentence': sentence,
                        'position': new_sentences.index(sentence)
                    })
            
            # Find modified sentences (semantic similarity)
            for i, old_sent in enumerate(old_sentences):
                if old_sent in new_set:
                    continue  # Exact match, no change
                
                # Find most similar sentence in new text
                best_similarity = 0.0
                best_match = None
                best_position = -1
                
                for j, new_sent in enumerate(new_sentences):
                    if new_sent in old_set:
                        continue  # Already matched
                    
                    similarity = self._calculate_sentence_similarity(old_sent, new_sent)
                    if similarity > best_similarity and similarity > 0.7:  # Threshold for considering it a modification
                        best_similarity = similarity
                        best_match = new_sent
                        best_position = j
                
                if best_match:
                    changes.append({
                        'type': 'modified',
                        'old_sentence': old_sent,
                        'new_sentence': best_match,
                        'old_position': i,
                        'new_position': best_position,
                        'similarity': best_similarity
                    })
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Sentence-level change detection failed: {e}")
            return []
    
    def _search_with_embeddings(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search using sentence transformers and FAISS"""
        if self.faiss_index is None or self.embedding_model is None:
            return []
        
        # Encode query
        query_embedding = self.embedding_model.encode([query])
        
        # Search in FAISS index
        scores, indices = self.faiss_index.search(query_embedding, min(top_k, len(self.documents)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.documents):
                results.append({
                    'text': self.documents[idx],
                    'metadata': self.document_metadata[idx],
                    'similarity_score': float(score),
                    'method': 'sentence_transformers'
                })
        
        return results
    
    def _search_basic(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Basic search using simple text matching"""
        if not self.documents:
            return []
        
        query_lower = query.lower()
        results = []
        
        for i, doc in enumerate(self.documents):
            doc_lower = doc.lower()
            # Simple scoring based on word matches
            query_words = query_lower.split()
            doc_words = doc_lower.split()
            
            matches = sum(1 for word in query_words if word in doc_words)
            if matches > 0:
                score = matches / len(query_words)
                results.append({
                    'text': doc,
                    'metadata': self.document_metadata[i],
                    'similarity_score': score,
                    'method': 'basic_text_match'
                })
        
        # Sort by score and return top-k
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:top_k]
    def _search_with_tfidf(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search using TF-IDF vectorization"""
        if self.tfidf_matrix is None or not SKLEARN_AVAILABLE:
            return self._search_basic(query, top_k)
        
        # Vectorize query
        query_vector = self.tfidf_vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append({
                    'text': self.documents[idx],
                    'metadata': self.document_metadata[idx],
                    'similarity_score': float(similarities[idx]),
                    'method': 'tfidf'
                })
        
        return results
    
    def _semantic_diff_embeddings(self, text1: str, text2: str) -> Dict[str, Any]:
        """Calculate semantic difference using embeddings"""
        if self.embedding_model is None:
            self._initialize_embedding_model()
        
        embeddings = self.embedding_model.encode([text1, text2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        return {
            'similarity_score': float(similarity),
            'difference_score': 1.0 - float(similarity),
            'method': 'sentence_transformers'
        }
    
    def _semantic_diff_tfidf(self, text1: str, text2: str) -> Dict[str, Any]:
        """Calculate semantic difference using TF-IDF"""
        if not SKLEARN_AVAILABLE:
            # Fallback to basic comparison
            return {
                'similarity_score': 1.0 if text1 == text2 else 0.5,
                'difference_score': 0.0 if text1 == text2 else 0.5,
                'method': 'basic_comparison'
            }
            
        vectorizer = TfidfVectorizer(stop_words='english')
        vectors = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
        
        return {
            'similarity_score': float(similarity),
            'difference_score': 1.0 - float(similarity),
            'method': 'tfidf'
        }
    
    def _calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """Calculate similarity between two sentences"""
        try:
            if self.use_sentence_transformers and self.embedding_model is not None:
                embeddings = self.embedding_model.encode([sent1, sent2])
                return float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
            elif SKLEARN_AVAILABLE:
                # Fallback to TF-IDF
                vectorizer = TfidfVectorizer(stop_words='english')
                vectors = vectorizer.fit_transform([sent1, sent2])
                return float(cosine_similarity(vectors[0], vectors[1])[0][0])
            else:
                # Basic word overlap similarity
                words1 = set(sent1.lower().split())
                words2 = set(sent2.lower().split())
                intersection = words1 & words2
                union = words1 | words2
                return len(intersection) / len(union) if union else 0.0
        except Exception:
            return 0.0
    
    def _update_index(self):
        """Update the vector index with new documents"""
        if not self.documents:
            return
        
        try:
            if self.use_sentence_transformers:
                self._update_embedding_index()
            else:
                self._update_tfidf_index()
            
            # Save index
            self._save_index()
            
        except Exception as e:
            self.logger.error(f"Failed to update index: {e}")
    
    def _update_embedding_index(self):
        """Update FAISS index with sentence embeddings"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not FAISS_AVAILABLE:
            return
        
        if self.embedding_model is None:
            self._initialize_embedding_model()
        
        if self.embedding_model is None:
            return
        
        # Generate embeddings for all documents
        embeddings = self.embedding_model.encode(self.documents)
        
        # Create or update FAISS index
        dimension = embeddings.shape[1]
        if self.faiss_index is None:
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
        else:
            self.faiss_index.reset()
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.faiss_index.add(embeddings.astype(np.float32))
    
    def _update_tfidf_index(self):
        """Update TF-IDF index"""
        if len(self.documents) > 0 and SKLEARN_AVAILABLE and self.tfidf_vectorizer is not None:
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.documents)
    
    def _save_index(self):
        """Save the vector index to disk"""
        index_data = {
            'documents': self.documents,
            'document_metadata': self.document_metadata,
            'use_sentence_transformers': self.use_sentence_transformers,
            'config': {
                'embedding_model': self.config.vector.embedding_model,
                'chunk_size': self.config.vector.chunk_size,
                'chunk_overlap': self.config.vector.chunk_overlap
            }
        }
        
        # Save metadata and documents
        metadata_path = Path(self.config.vector.index_dir) / 'index_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(index_data, f, indent=2, default=str)
        
        # Save FAISS index if using embeddings
        if self.use_sentence_transformers and self.faiss_index is not None:
            faiss_path = Path(self.config.vector.index_dir) / 'faiss_index.bin'
            faiss.write_index(self.faiss_index, str(faiss_path))
        
        # Save TF-IDF components if using TF-IDF
        if not self.use_sentence_transformers and self.tfidf_matrix is not None:
            tfidf_path = Path(self.config.vector.index_dir) / 'tfidf_components.pkl'
            with open(tfidf_path, 'wb') as f:
                pickle.dump({
                    'vectorizer': self.tfidf_vectorizer,
                    'matrix': self.tfidf_matrix
                }, f)
    
    def _load_index(self):
        """Load existing vector index from disk"""
        try:
            metadata_path = Path(self.config.vector.index_dir) / 'index_metadata.json'
            if not metadata_path.exists():
                return
            
            with open(metadata_path, 'r') as f:
                index_data = json.load(f)
            
            self.documents = index_data.get('documents', [])
            self.document_metadata = index_data.get('document_metadata', [])
            
            # Load FAISS index if available
            if self.use_sentence_transformers:
                faiss_path = Path(self.config.vector.index_dir) / 'faiss_index.bin'
                if faiss_path.exists():
                    self._initialize_embedding_model()
                    if self.embedding_model is not None:
                        self.faiss_index = faiss.read_index(str(faiss_path))
            
            # Load TF-IDF components if available
            else:
                tfidf_path = Path(self.config.vector.index_dir) / 'tfidf_components.pkl'
                if tfidf_path.exists():
                    with open(tfidf_path, 'rb') as f:
                        components = pickle.load(f)
                        self.tfidf_vectorizer = components['vectorizer']
                        self.tfidf_matrix = components['matrix']
            
            self.logger.info(f"Loaded vector index with {len(self.documents)} documents")
            
        except Exception as e:
            self.logger.warning(f"Could not load existing index: {e}")
            self.documents = []
            self.document_metadata = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        return {
            'total_documents': len(self.documents),
            'index_method': 'sentence_transformers' if self.use_sentence_transformers else 'tfidf',
            'embedding_model': self.config.vector.embedding_model if self.use_sentence_transformers else None,
            'index_size_mb': self._get_index_size_mb(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_index_size_mb(self) -> float:
        """Calculate total size of index files in MB"""
        total_size = 0
        index_dir = Path(self.config.vector.index_dir)
        
        for file_path in index_dir.glob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size / (1024 * 1024)
    
    def clear_index(self):
        """Clear the entire vector index"""
        self.documents = []
        self.document_metadata = []
        self.faiss_index = None
        self.tfidf_matrix = None
        
        # Remove index files
        index_dir = Path(self.config.vector.index_dir)
        for file_path in index_dir.glob('*'):
            if file_path.is_file():
                file_path.unlink()
        
        self.logger.info("Vector index cleared")


# Global vector index instance
vector_index = VectorIndex()