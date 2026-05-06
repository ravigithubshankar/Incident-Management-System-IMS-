import React, { useState } from 'react'
import { X } from 'lucide-react'

interface RCAFormProps {
  incidentId: string
  onClose: () => void
  onSuccess: () => void
}

const RCAForm: React.FC<RCAFormProps> = ({ incidentId, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    start_time: '',
    end_time: '',
    root_cause_category: '',
    fix_applied: '',
    prevention_steps: '',
    created_by: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const API_BASE = import.meta.env.VITE_API_URL ?? ''

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const validateForm = () => {
    if (!formData.start_time || !formData.end_time) {
      return 'Start time and end time are required'
    }
    
    if (new Date(formData.end_time) <= new Date(formData.start_time)) {
      return 'End time must be after start time'
    }
    
    if (!formData.root_cause_category) {
      return 'Root cause category is required'
    }
    
    if (formData.fix_applied.length < 50) {
      return 'Fix applied must be at least 50 characters'
    }
    
    if (formData.prevention_steps.length < 50) {
      return 'Prevention steps must be at least 50 characters'
    }
    
    if (!formData.created_by.trim()) {
      return 'Created by is required'
    }
    
    return ''
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }
    
    setError('')
    setIsSubmitting(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/incidents/${incidentId}/rca`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'dev-api-key-12345'
        },
        body: JSON.stringify({
          ...formData,
          start_time: new Date(formData.start_time).toISOString(),
          end_time: new Date(formData.end_time).toISOString()
        })
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText || 'Failed to create RCA')
      }
      
      const result = await response.json()
      onSuccess()
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-screen overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Complete Root Cause Analysis</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Incident Start *
              </label>
              <input
                type="datetime-local"
                name="start_time"
                value={formData.start_time}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Incident End *
              </label>
              <input
                type="datetime-local"
                name="end_time"
                value={formData.end_time}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Root Cause Category *
            </label>
            <select
              name="root_cause_category"
              value={formData.root_cause_category}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select a category</option>
              <option value="DB_FAILURE">Database Failure</option>
              <option value="NETWORK">Network</option>
              <option value="MISCONFIGURATION">Misconfiguration</option>
              <option value="CAPACITY">Capacity</option>
              <option value="SOFTWARE_BUG">Software Bug</option>
              <option value="EXTERNAL_DEPENDENCY">External Dependency</option>
              <option value="HUMAN_ERROR">Human Error</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fix Applied * ({formData.fix_applied.length}/50 chars)
            </label>
            <textarea
              name="fix_applied"
              value={formData.fix_applied}
              onChange={handleInputChange}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe the fix that was applied to resolve this incident..."
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Prevention Steps * ({formData.prevention_steps.length}/50 chars)
            </label>
            <textarea
              name="prevention_steps"
              value={formData.prevention_steps}
              onChange={handleInputChange}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe steps to prevent this incident from recurring..."
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Created By *
            </label>
            <input
              type="text"
              name="created_by"
              value={formData.created_by}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your name or team name"
              required
            />
          </div>
        </form>

        <div className="flex justify-end space-x-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : 'Submit RCA'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default RCAForm
