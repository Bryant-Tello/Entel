import React, { useState, useEffect } from 'react'
import { searchAPI, analysisAPI, uploadAPI, deleteAPI, transcriptsAPI } from './services/api'
import './index.css'

function App() {
  const [activeTab, setActiveTab] = useState('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [topics, setTopics] = useState([])
  const [groupedTopics, setGroupedTopics] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTranscript, setSelectedTranscript] = useState(null)
  const [showTranscriptModal, setShowTranscriptModal] = useState(false)
  const [showCleanedText, setShowCleanedText] = useState(false)
  const [currentPage, setCurrentPage] = useState({})
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false)
  const [uploadFiles, setUploadFiles] = useState([]) // Cambiar a array para múltiples archivos
  const [uploadSuccess, setUploadSuccess] = useState(null)

  useEffect(() => {
    if (activeTab === 'topics') {
      loadTopics()
    }
  }, [activeTab])

  const loadTopics = async () => {
    try {
      setLoading(true)
      const response = await analysisAPI.getTopics(10, 1)
      console.log('Response data:', response.data)
      setTopics(response.data.topics || [])
      setGroupedTopics(response.data.grouped_by_category || {})
      console.log('Grouped topics:', response.data.grouped_by_category)
      setError(null)
    } catch (err) {
      console.error('Error cargando temas:', err)
      setError('Error cargando temas: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleViewTranscript = async (filename, showCleaned = false) => {
    try {
      const response = await transcriptsAPI.get(filename)
      setSelectedTranscript({
        filename: filename,
        content: response.data.content || 'Contenido no disponible',
        cleaned_content: response.data.cleaned_content || 'Contenido limpio no disponible'
      })
      setShowCleanedText(showCleaned)
      setShowTranscriptModal(true)
    } catch (err) {
      setError('Error cargando transcripción: ' + err.message)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    try {
      setLoading(true)
      setError(null)
      const response = await searchAPI.search(searchQuery)
      setSearchResults(response.data.results || [])
    } catch (err) {
      setError('Error en búsqueda: ' + err.message)
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  const formatCategory = (category) => {
    if (!category) return 'Sin clasificar'
    return category
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const handleFileUpload = async (e) => {
    e.preventDefault()
    if (uploadFiles.length === 0) return

    try {
      setLoading(true)
      setError(null)
      setUploadSuccess(null)
      
      const results = []
      const errors = []
      
      // Subir archivos uno por uno
      for (const file of uploadFiles) {
        try {
          const response = await uploadAPI.uploadTranscript(file)
          const embeddingStatus = response.data.embedding_generated ? 'Si' : 'No'
          const classificationStatus = response.data.classification_done ? 'Si' : 'No'
          const category = response.data.category ? ` (${response.data.category})` : ''
          results.push(`${response.data.filename} - Embedding: ${embeddingStatus}, Clasificación: ${classificationStatus}${category}`)
        } catch (err) {
          errors.push(`${file.name}: ${err.message}`)
        }
      }
      
      // Mostrar resultados
      let message = ''
      if (results.length > 0) {
        message = `${results.length} archivo(s) subido(s) exitosamente:\n${results.join('\n')}`
      }
      if (errors.length > 0) {
        message += (message ? '\n\n' : '') + `Errores:\n${errors.join('\n')}`
      }
      
      setUploadSuccess(message)
      setUploadFiles([])
      
      // Resetear input
      e.target.reset()
    } catch (err) {
      setError('Error subiendo archivos: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteTranscript = async (filename) => {
    try {
      await deleteAPI.deleteTranscript(filename)
      setUploadSuccess(`Transcripción "${filename}" eliminada exitosamente`)
      setTimeout(() => setUploadSuccess(null), 3000)
      
      // Recargar datos según la pestaña activa
      if (activeTab === 'topics') {
        loadTopics()
      }
    } catch (err) {
      setError('Error eliminando transcripción: ' + err.message)
    }
  }

  const handleDeleteAllTranscripts = async () => {
    if (!showDeleteAllConfirm) {
      setShowDeleteAllConfirm(true)
      return
    }

    try {
      setLoading(true)
      await deleteAPI.deleteAllTranscripts()
      setUploadSuccess('Todas las transcripciones eliminadas exitosamente')
      setTimeout(() => setUploadSuccess(null), 3000)
      setShowDeleteAllConfirm(false)
      
      // Recargar datos
      if (activeTab === 'topics') {
        loadTopics()
      }
    } catch (err) {
      setError('Error eliminando todas las transcripciones: ' + err.message)
      setShowDeleteAllConfirm(false)
    } finally {
      setLoading(false)
    }
  }

  const getPaginatedTranscripts = (transcripts, category) => {
    const page = currentPage[category] || 1
    const itemsPerPage = 10
    const start = (page - 1) * itemsPerPage
    const end = start + itemsPerPage
    return {
      items: transcripts.slice(start, end),
      totalPages: Math.ceil(transcripts.length / itemsPerPage),
      currentPage: page,
      total: transcripts.length
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1>Sistema de Analisis de Transcripciones</h1>
        <p>Analisis semantico de llamadas de atencion al cliente - Entel GenAI</p>
      </div>

      <div className="content">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            Busqueda
          </button>
          <button
            className={`tab ${activeTab === 'topics' ? 'active' : ''}`}
            onClick={() => setActiveTab('topics')}
          >
            Temas
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {activeTab === 'search' && (
          <div className="search-section">
            <div style={{ marginBottom: '30px' }}>
              <h2>Subir Transcripciones</h2>
              <form onSubmit={handleFileUpload} className="upload-form">
                <div className="upload-box">
                  <input
                    type="file"
                    accept=".txt"
                    multiple
                    onChange={(e) => {
                      const files = Array.from(e.target.files || [])
                      setUploadFiles(files)
                    }}
                    className="file-input"
                    disabled={loading}
                  />
                  {uploadFiles.length > 0 && (
                    <div style={{ marginTop: '15px', width: '100%' }}>
                      <h4>Archivos seleccionados ({uploadFiles.length}):</h4>
                      {uploadFiles.map((file, idx) => (
                        <div key={idx} style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '8px',
                          marginBottom: '8px',
                          background: '#f0f0f0',
                          borderRadius: '5px'
                        }}>
                          <span>{file.name}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newFiles = uploadFiles.filter((_, i) => i !== idx)
                              setUploadFiles(newFiles)
                            }}
                            style={{
                              padding: '5px 10px',
                              background: '#dc3545',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                          >
                            Eliminar
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <button
                    type="submit"
                    className="upload-button"
                    disabled={loading || uploadFiles.length === 0}
                    style={{ marginTop: '15px' }}
                  >
                    {loading ? 'Subiendo...' : `Subir ${uploadFiles.length} Transcripcion${uploadFiles.length !== 1 ? 'es' : ''}`}
                  </button>
                </div>
              </form>

              {uploadSuccess && (
                <div className="success-message">{uploadSuccess}</div>
              )}
            </div>

            <div style={{ marginTop: '40px', borderTop: '2px solid #ddd', paddingTop: '30px' }}>
              <h2>Buscar Transcripciones</h2>
              <form onSubmit={handleSearch} className="search-box">
                <input
                  type="text"
                  className="search-input"
                  placeholder="Buscar palabras clave o frases en las transcripciones..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <button
                  type="submit"
                  className="search-button"
                  disabled={loading || !searchQuery.trim()}
                >
                  {loading ? 'Buscando...' : 'Buscar'}
                </button>
              </form>
            </div>

            {loading && <div className="loading">Buscando...</div>}

            {!loading && searchResults.length > 0 && (
              <div className="results">
                <h2>Resultados ({searchResults.length})</h2>
                {searchResults.map((result, idx) => (
                  <div key={idx} className="result-card">
                    <div className="result-header">
                      <span className="result-title">{result.filename}</span>
                      <span className="result-similarity">
                        {(result.similarity * 100).toFixed(1)}% relevante
                      </span>
                    </div>
                    {result.category && (
                      <span className="result-category">
                        {formatCategory(result.category)}
                      </span>
                    )}
                    <div className="result-snippet">{result.snippet}</div>
                    <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                      <button
                        onClick={() => handleViewTranscript(result.filename, false)}
                        style={{
                          padding: '5px 10px',
                          background: '#4a90e2',
                          color: 'white',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontSize: '0.9em'
                        }}
                      >
                        Ver Completo
                      </button>
                      <button
                        onClick={() => handleViewTranscript(result.filename, true)}
                        style={{
                          padding: '5px 10px',
                          background: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer',
                          fontSize: '0.9em'
                        }}
                      >
                        Ver Limpio
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!loading && searchResults.length === 0 && searchQuery && (
              <div className="empty">No se encontraron resultados</div>
            )}

            {!loading && searchResults.length === 0 && !searchQuery && (
              <div style={{ marginTop: '40px' }}>
                <div className="empty" style={{ marginTop: '30px', marginBottom: '30px' }}>
                  Sube transcripciones arriba y luego busca en ellas
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'topics' && (
          <div>
            <h2>Temas Principales</h2>
            {loading && <div className="loading">Cargando temas...</div>}

            {error && <div className="error">{error}</div>}

            {!loading && !error && Object.keys(groupedTopics).length > 0 && (
              <div style={{ marginTop: '20px' }}>
                {/* Botón para eliminar todas */}
                <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                  <button
                    onClick={handleDeleteAllTranscripts}
                    style={{
                      padding: '10px 20px',
                      background: showDeleteAllConfirm ? '#dc3545' : '#ff6b6b',
                      color: 'white',
                      border: 'none',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      fontSize: '1em',
                      fontWeight: 'bold'
                    }}
                  >
                    {showDeleteAllConfirm ? 'Confirmar Eliminar Todas' : 'Eliminar Todas las Conversaciones'}
                  </button>
                </div>

                {Object.entries(groupedTopics).map(([category, transcripts]) => {
                  const paginated = getPaginatedTranscripts(transcripts, category)
                  return (
                  <div key={category} style={{ marginBottom: '40px', border: '1px solid #ddd', borderRadius: '8px', padding: '20px', background: '#f9f9f9' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                      <h3 style={{ margin: 0, color: '#4a90e2' }}>
                        {formatCategory(category)} ({transcripts.length} transcripción{transcripts.length !== 1 ? 'es' : ''})
                      </h3>
                      {paginated.totalPages > 1 && (
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                          <button
                            onClick={() => setCurrentPage({...currentPage, [category]: Math.max(1, (currentPage[category] || 1) - 1)})}
                            disabled={paginated.currentPage === 1}
                            style={{
                              padding: '5px 10px',
                              background: paginated.currentPage === 1 ? '#ccc' : '#4a90e2',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: paginated.currentPage === 1 ? 'not-allowed' : 'pointer'
                            }}
                          >
                            Anterior
                          </button>
                          <span>Página {paginated.currentPage} de {paginated.totalPages}</span>
                          <button
                            onClick={() => setCurrentPage({...currentPage, [category]: Math.min(paginated.totalPages, (currentPage[category] || 1) + 1)})}
                            disabled={paginated.currentPage === paginated.totalPages}
                            style={{
                              padding: '5px 10px',
                              background: paginated.currentPage === paginated.totalPages ? '#ccc' : '#4a90e2',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: paginated.currentPage === paginated.totalPages ? 'not-allowed' : 'pointer'
                            }}
                          >
                            Siguiente
                          </button>
                        </div>
                      )}
                    </div>
                    
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '5px' }}>
                        <thead>
                          <tr style={{ background: '#4a90e2', color: 'white' }}>
                            <th style={{ padding: '12px', textAlign: 'left', border: '1px solid #ddd' }}>Conversación</th>
                            <th style={{ padding: '12px', textAlign: 'left', border: '1px solid #ddd' }}>Tema Principal</th>
                            <th style={{ padding: '12px', textAlign: 'left', border: '1px solid #ddd' }}>Palabras Clave</th>
                            <th style={{ padding: '12px', textAlign: 'left', border: '1px solid #ddd' }}>Acciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {paginated.items.map((trans, tIdx) => (
                            <tr key={tIdx} style={{ borderBottom: '1px solid #ddd' }}>
                              <td style={{ padding: '10px', border: '1px solid #ddd' }}>{trans.conversacion}</td>
                              <td style={{ padding: '10px', border: '1px solid #ddd', maxWidth: '300px' }}>
                                {trans.tema_principal || 'N/A'}
                              </td>
                              <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                                {trans.palabras_clave?.join(', ') || 'N/A'}
                              </td>
                              <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                  <button
                                    onClick={() => handleViewTranscript(trans.conversacion, false)}
                                    style={{
                                      padding: '5px 10px',
                                      background: '#4a90e2',
                                      color: 'white',
                                      border: 'none',
                                      borderRadius: '3px',
                                      cursor: 'pointer',
                                      fontSize: '0.9em'
                                    }}
                                  >
                                    Ver
                                  </button>
                                  <button
                                    onClick={() => handleViewTranscript(trans.conversacion, true)}
                                    style={{
                                      padding: '5px 10px',
                                      background: '#28a745',
                                      color: 'white',
                                      border: 'none',
                                      borderRadius: '3px',
                                      cursor: 'pointer',
                                      fontSize: '0.9em'
                                    }}
                                  >
                                    Ver Limpio
                                  </button>
                                  <button
                                    onClick={() => handleDeleteTranscript(trans.conversacion)}
                                    style={{
                                      padding: '5px 10px',
                                      background: '#dc3545',
                                      color: 'white',
                                      border: 'none',
                                      borderRadius: '3px',
                                      cursor: 'pointer',
                                      fontSize: '0.9em'
                                    }}
                                  >
                                    Eliminar
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  )
                })}
              </div>
            )}

            {!loading && !error && Object.keys(groupedTopics).length === 0 && topics.length === 0 && (
              <div className="empty">No hay temas disponibles. Sube transcripciones para generar temas.</div>
            )}

            {!loading && !error && Object.keys(groupedTopics).length === 0 && topics.length > 0 && (
              <div className="empty">
                Hay {topics.length} tema(s) pero no hay transcripciones clasificadas. 
                Las transcripciones aparecerán aquí después de ser clasificadas automáticamente.
              </div>
            )}

            {/* Modal de confirmación para eliminar todas */}
            {showDeleteAllConfirm && (
              <div style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1001
              }}>
                <div style={{
                  background: 'white',
                  borderRadius: '8px',
                  padding: '30px',
                  maxWidth: '500px',
                  textAlign: 'center'
                }}>
                  <h3 style={{ marginTop: 0, color: '#dc3545' }}>Confirmar Eliminación</h3>
                  <p>¿Estás seguro de que deseas eliminar TODAS las conversaciones?</p>
                  <p style={{ color: '#666', fontSize: '0.9em' }}>Esta acción no se puede deshacer.</p>
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '20px' }}>
                    <button
                      onClick={handleDeleteAllTranscripts}
                      style={{
                        padding: '10px 20px',
                        background: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontSize: '1em'
                      }}
                    >
                      Sí, Eliminar Todas
                    </button>
                    <button
                      onClick={() => setShowDeleteAllConfirm(false)}
                      style={{
                        padding: '10px 20px',
                        background: '#6c757d',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontSize: '1em'
                      }}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}

        {/* Modal para ver transcripción completa - Disponible en todas las pestañas */}
        {showTranscriptModal && selectedTranscript && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              background: 'white',
              borderRadius: '8px',
              padding: '20px',
              maxWidth: '80%',
              maxHeight: '80%',
              overflow: 'auto',
              position: 'relative'
            }}>
              <button
                onClick={() => {
                  setShowTranscriptModal(false)
                  setSelectedTranscript(null)
                }}
                style={{
                  position: 'absolute',
                  top: '10px',
                  right: '10px',
                  background: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '50%',
                  width: '30px',
                  height: '30px',
                  cursor: 'pointer',
                  fontSize: '18px'
                }}
              >
                ×
              </button>
              <h3 style={{ marginTop: 0 }}>{selectedTranscript.filename}</h3>
              <div style={{ marginBottom: '15px', display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => setShowCleanedText(false)}
                  style={{
                    padding: '8px 15px',
                    background: showCleanedText ? '#e0e0e0' : '#4a90e2',
                    color: showCleanedText ? '#333' : 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    fontWeight: showCleanedText ? 'normal' : 'bold'
                  }}
                >
                  Texto Original
                </button>
                <button
                  onClick={() => setShowCleanedText(true)}
                  style={{
                    padding: '8px 15px',
                    background: showCleanedText ? '#28a745' : '#e0e0e0',
                    color: showCleanedText ? 'white' : '#333',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    fontWeight: showCleanedText ? 'bold' : 'normal'
                  }}
                >
                  Texto Limpio
                </button>
              </div>
              <pre style={{
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                background: '#f5f5f5',
                padding: '15px',
                borderRadius: '5px',
                maxHeight: '60vh',
                overflow: 'auto'
              }}>
                {showCleanedText ? (selectedTranscript.cleaned_content || 'Contenido limpio no disponible') : (selectedTranscript.content || 'Contenido no disponible')}
              </pre>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

export default App

