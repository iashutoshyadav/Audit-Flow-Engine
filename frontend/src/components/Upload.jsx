import React, { useRef, useState } from 'react'

const Upload = ({ onUpload, loading, progress, statusMessage }) => {
    const fileInputRef = useRef(null)
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState(null)

    const handleChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0]
            setSelectedFile(file)
            onUpload(file)
        }
    }

    const handleDrag = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true)
        } else if (e.type === "dragleave") {
            setDragActive(false)
        }
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0]
            if (file.type === 'application/pdf') {
                setSelectedFile(file)
                onUpload(file)
            } else {
                alert('Please upload a PDF file')
            }
        }
    }

    return (
        <div className="upload-container">
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleChange}
                accept=".pdf"
                style={{ display: 'none' }}
            />

            <div
                className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !loading && fileInputRef.current.click()}
            >
                <div className="upload-icon">📄</div>
                <div className="upload-text">
                    <h3>{selectedFile ? selectedFile.name : 'Drop your PDF here'}</h3>
                    <p>or click to browse • PDF files only</p>
                </div>
            </div>

            <button
                onClick={() => fileInputRef.current.click()}
                disabled={loading}
                className="upload-btn"
            >
                {loading ? '⚡ Processing...' : '📤 Select PDF Document'}
            </button>

            {loading && (
                <div className="status-container">
                    <div className="status-message">
                        {statusMessage || 'Processing your document...'}
                    </div>
                </div>
            )}
        </div>
    )
}

export default Upload
