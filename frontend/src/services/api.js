import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const transcriptsAPI = {
  get: (id) => api.get(`/api/transcripts/${id}`),
}

export const searchAPI = {
  search: (query, limit = 10, threshold = 0.7) =>
    api.post('/api/search', { query, limit, threshold }),
}

export const analysisAPI = {
  getTopics: (numTopics = 10, minTopicSize = 3) =>
    api.get('/api/topics', { params: { num_topics: numTopics, min_topic_size: minTopicSize } }),
}

export const uploadAPI = {
  uploadTranscript: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/upload/transcript', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

export const deleteAPI = {
  deleteTranscript: (filename) => api.delete(`/api/delete/transcript/${filename}`),
  deleteAllTranscripts: () => api.delete('/api/delete/all'),
}

export default api

