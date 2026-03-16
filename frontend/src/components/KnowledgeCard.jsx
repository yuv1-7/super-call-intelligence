import { useState, useEffect } from 'react';

export default function KnowledgeCard({ docs }) {
    const [expandedDocs, setExpandedDocs] = useState({});

    // Auto-expand the first article when docs arrive
    useEffect(() => {
        if (docs && docs.length > 0 && Object.keys(expandedDocs).length === 0) {
            setExpandedDocs({ [docs[0].document_id || 0]: true });
        }
    }, [docs]);

    const toggleDoc = (docId) => {
        setExpandedDocs((prev) => ({ ...prev, [docId]: !prev[docId] }));
    };

    if (!docs || docs.length === 0) {
        return (
            <div className="card knowledge compact-empty">
                <div className="card-header">
                    <div className="card-icon">📚</div>
                    <div>
                        <div className="card-title">Knowledge Articles</div>
                        <div className="card-subtitle">No articles loaded</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="card knowledge">
            <div className="card-header">
                <div className="card-icon">📚</div>
                <div>
                    <div className="card-title">Knowledge Articles</div>
                    <div className="card-subtitle">{docs.length} relevant document{docs.length !== 1 ? 's' : ''} found</div>
                </div>
            </div>
            <div className="card-body">
                {docs.map((doc, idx) => (
                    <div
                        key={doc.document_id || idx}
                        className={`knowledge-article ${expandedDocs[doc.document_id || idx] ? 'expanded' : ''}`}
                        onClick={() => toggleDoc(doc.document_id || idx)}
                    >
                        {doc.document_id && <div className="doc-id">{doc.document_id}</div>}
                        <h4>
                            {doc.title}
                            <span className="expand-icon">▼</span>
                        </h4>
                        <p>{doc.content}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
