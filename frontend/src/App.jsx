import { useState, useEffect } from 'react'
import Upload from './components/Upload'
import ResultsTable from './components/ResultsTable'
import './App.css'

function App() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [targetProgress, setTargetProgress] = useState(0)
    const [statusMessage, setStatusMessage] = useState("")
    const [error, setError] = useState(null)

    const API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        if (!loading) return;

        const interval = setInterval(() => {
            setProgress(prev => {
                if (prev < targetProgress) {
                    return Math.min(prev + 1, targetProgress);
                }
                if (prev < 100 && prev >= targetProgress) {
                    return Math.min(prev + 0.5, targetProgress + 5);
                }
                return prev;
            });
        }, 100); // Update every 100ms for smooth animation

        return () => clearInterval(interval);
    }, [loading, targetProgress]);

    useEffect(() => {
        console.log('🔄 Data state changed:', data);
        if (data) {
            console.log(' Results section should now be visible!');
            console.log('   - filename:', data.filename);
            console.log('   - extracted_data:', data.extracted_data);
        }
    }, [data]);

    const handleUpload = async (file) => {
        setLoading(true)
        setError(null)
        setProgress(0)
        setTargetProgress(0)
        setData(null)
        setStatusMessage("Initializing...")

        const formData = new FormData()
        formData.append('file', file)

        try {
            const response = await fetch(`${API_URL}/api/upload`, {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `Upload failed: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");

                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const event = JSON.parse(line);
                        console.log(' Received event:', event);

                        if (event.status === "error") {
                            throw new Error(event.message);
                        }

                        if (event.progress) {
                            setTargetProgress(event.progress);
                        }

                        if (event.message) {
                            setStatusMessage(event.message);
                        }

                        if (event.status === "complete" && event.data) {
                            console.log(' Upload complete! Data:', event.data);
                            setProgress(100);
                            setTargetProgress(100);
                            setData(event.data);
                            console.log(' Data state updated');
                        }
                    } catch (e) {
                        console.error(" Error parsing JSON stream:", e, "Line:", line);
                    }
                }
            }

        } catch (err) {
            console.error(' Upload error:', err);
            setError(err.message)
        } finally {
            console.log(' Upload finished, setting loading to false');
            setLoading(false)
            setStatusMessage("")
        }
    }

    return (
        <div className="container">
            <div className="header-section">
                <h1>Audit Flow Engine</h1>
                <p>AI-powered analysis for Annual Reports • Fast • Accurate • Reliable</p>
            </div>

            <div className="card upload-card">
                <Upload
                    onUpload={handleUpload}
                    loading={loading}
                    progress={progress}
                    statusMessage={statusMessage}
                />

                {loading && (
                    <div className="progress-container">
                        <div className="progress-bar-wrapper">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${progress}%` }}
                            ></div>
                        </div>
                        <div className="progress-label">
                            <span>{statusMessage}</span>
                            <span>{progress}%</span>
                        </div>
                    </div>
                )}
            </div>

            {error && <div className="error-banner"> {error}</div>}

            {data && (
                <div className="results-section fade-in">
                    <div className="results-header">
                        <h2>Extraction Complete</h2>
                        <a
                            href={`${API_URL}/api/download/${encodeURIComponent(data.filename)}`}
                            className="download-btn-premium"
                            download
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            📥 Download Excel Report
                        </a>
                    </div>
                    <div className="results-summary">
                        <div className="summary-card">
                            <h3>📊 Processing Summary</h3>
                            <p><strong>Year Headers:</strong> {data.extracted_data?.year_headers?.join(', ') || 'N/A'}</p>
                            <p><strong>Rows Processed:</strong> {data.extracted_data?.row_count || 0}</p>
                            <p><strong>Status:</strong> <span className="success-badge">✓ Success</span></p>
                        </div>
                        <div className="summary-card">
                            <h3>📄 What's in the Excel?</h3>
                            <ul>
                                <li>Financial Statement (formatted with formulas)</li>
                                <li>Calculated metrics (EBITDA, PBT, PAT, Margins)</li>
                                <li>Raw data sheet (for debugging)</li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
