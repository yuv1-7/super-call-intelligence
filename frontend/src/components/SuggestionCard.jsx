export default function SuggestionCard({ suggestion, isProcessing }) {
    if (isProcessing && !suggestion) {
        return (
            <div className="card suggestion">
                <div className="card-header">
                    <div className="card-icon">💡</div>
                    <div>
                        <div className="card-title">Suggested Response</div>
                        <div className="card-subtitle">Generating...</div>
                    </div>
                </div>
                <div className="card-body">
                    <div className="suggestion-shimmer">
                        <div className="shimmer-line" />
                        <div className="shimmer-line" />
                        <div className="shimmer-line" />
                    </div>
                </div>
            </div>
        );
    }

    if (!suggestion) {
        return (
            <div className="card suggestion empty">
                <div className="empty-state">
                    <div className="empty-icon">💡</div>
                    <h3>Suggested Response</h3>
                    <p>AI-generated talking points for the agent will appear here</p>
                </div>
            </div>
        );
    }

    // Render as a single flowing block with visual paragraph breaks.
    // Previous implementation split on \n\n into separate highlighted bubbles
    // which made long scripts hard to read aloud.
    const paragraphs = suggestion
        .split('\n\n')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    const isUpdating = isProcessing && suggestion;

    return (
        <div className={`card suggestion${isUpdating ? ' updating' : ''}`}>
            <div className="card-header">
                <div className="card-icon">💡</div>
                <div>
                    <div className="card-title">Suggested Response</div>
                    <div className="card-subtitle">
                        {isUpdating ? 'Updating...' : 'Ready to use'}
                    </div>
                </div>
            </div>
            <div className="card-body">
                <div className="suggestion-text">
                    <span className="highlight-script">
                        {paragraphs.map((text, idx) => (
                            <span key={idx}>
                                {idx > 0 && <><br /><br /></>}
                                {text}
                            </span>
                        ))}
                    </span>
                    {isProcessing && (
                        <div className="suggestion-shimmer" style={{ marginTop: '4px' }}>
                            <div className="shimmer-line" />
                            <div className="shimmer-line" />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
