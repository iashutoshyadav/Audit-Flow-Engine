import React from 'react'

const ResultsTable = ({ data }) => {
    if (!data) return null;

    return (
        <div className="results-table">
            <h3>Extracted Data Preview</h3>
            <table>
                <thead>
                    <tr>
                        <th>Line Item</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {Object.entries(data).map(([key, value]) => (
                        <tr key={key}>
                            <td>{key}</td>
                            <td>{value !== null ? value : <span className="missing">Not Found</span>}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

export default ResultsTable
