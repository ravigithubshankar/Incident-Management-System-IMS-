import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useIncident, useUpdateIncidentStatus } from '../hooks/useIncidents'
import RCAForm from '../components/RCAForm'
import { ArrowLeft, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface Incident {
  id: string
  component_id: string
  component_type: string
  severity: string
  status: string
  title: string
  signal_count: number
  created_at: string
  updated_at: string
  closed_at?: string
  signals?: any[]
  rca?: any
}

const Detail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: incident, isLoading, error } = useIncident(id || '')
  const updateStatus = useUpdateIncidentStatus()
  const [showRCAForm, setShowRCAForm] = useState(false)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OPEN': return 'text-red-600'
      case 'INVESTIGATING': return 'text-yellow-600'
      case 'RESOLVED': return 'text-green-600'
      case 'CLOSED': return 'text-gray-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN': return <AlertTriangle className="w-5 h-5 text-red-500" />
      case 'INVESTIGATING': return <Clock className="w-5 h-5 text-yellow-500" />
      case 'RESOLVED': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'CLOSED': return <XCircle className="w-5 h-5 text-gray-500" />
      default: return null
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'P0': return 'bg-red-100 text-red-800 border-red-200'
      case 'P1': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'P2': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'P3': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getNextStatuses = (currentStatus: string) => {
    switch (currentStatus) {
      case 'OPEN': return ['INVESTIGATING']
      case 'INVESTIGATING': return ['RESOLVED']
      case 'RESOLVED': return incident?.rca ? ['CLOSED'] : []
      case 'CLOSED': return []
      default: return []
    }
  }

  const handleStatusUpdate = (newStatus: string) => {
    if (id) {
      updateStatus.mutate({ id, status: newStatus })
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !incident) {
    return (
      <div className="text-red-600 text-center py-8">
        Error loading incident: {(error as Error)?.message || 'Incident not found'}
      </div>
    )
  }

  const nextStatuses = getNextStatuses(incident.status)

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 flex items-center text-blue-600 hover:text-blue-900"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Dashboard
      </button>

      {/* Incident Header */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{incident.title}</h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>Component: {incident.component_id}</span>
              <span>•</span>
              <span>Type: {incident.component_type}</span>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(incident.severity)}`}>
              {incident.severity}
            </span>
            <div className="flex items-center space-x-2">
              {getStatusIcon(incident.status)}
              <span className={`font-medium ${getStatusColor(incident.status)}`}>
                {incident.status}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-500">Signal Count:</span>
            <span className="ml-2 text-gray-900">{incident.signal_count}</span>
          </div>
          <div>
            <span className="font-medium text-gray-500">Created:</span>
            <span className="ml-2 text-gray-900">{formatDate(incident.created_at)}</span>
          </div>
          <div>
            <span className="font-medium text-gray-500">Updated:</span>
            <span className="ml-2 text-gray-900">{formatDate(incident.updated_at)}</span>
          </div>
        </div>

        {/* Status Transition Button */}
        {nextStatuses.length > 0 && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Update Status:
            </label>
            <div className="flex space-x-2">
              {nextStatuses.map(status => (
                <button
                  key={status}
                  onClick={() => handleStatusUpdate(status)}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  disabled={updateStatus.isPending}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* RCA Section */}
      {(incident.status === 'RESOLVED' || incident.status === 'CLOSED') && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Root Cause Analysis</h2>
          
          {incident.rca ? (
            <div className="space-y-4">
              <div>
                <span className="font-medium text-gray-700">MTTR:</span>
                <span className="ml-2 text-gray-900">
                  {incident.rca.mttr_minutes.toFixed(1)} minutes
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Root Cause:</span>
                <span className="ml-2 text-gray-900">{incident.rca.root_cause_category}</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Fix Applied:</span>
                <p className="mt-1 text-gray-900">{incident.rca.fix_applied}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Prevention Steps:</span>
                <p className="mt-1 text-gray-900">{incident.rca.prevention_steps}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Created By:</span>
                <span className="ml-2 text-gray-900">{incident.rca.created_by}</span>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-gray-600 mb-4">No RCA has been completed for this incident.</p>
              {incident.status === 'RESOLVED' && (
                <button
                  onClick={() => setShowRCAForm(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Complete RCA
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* RCA Form Modal */}
      {showRCAForm && (
        <RCAForm
          incidentId={incident.id}
          onClose={() => setShowRCAForm(false)}
          onSuccess={() => {
            setShowRCAForm(false)
            // Refresh incident data
            window.location.reload()
          }}
        />
      )}

      {/* Signal Timeline */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Signal Timeline</h2>
        
        {incident.signals && incident.signals.length > 0 ? (
          <div className="space-y-4">
            {incident.signals.map((signal, index) => (
              <div key={signal.id} className="border-l-4 border-gray-200 pl-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(signal.severity)}`}>
                        {signal.severity}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatDate(signal.timestamp)}
                      </span>
                    </div>
                    <p className="text-gray-900">{signal.message}</p>
                    {signal.metadata && Object.keys(signal.metadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                          View Metadata
                        </summary>
                        <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                          {JSON.stringify(signal.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No signals found for this incident.</p>
        )}
      </div>
    </div>
  )
}

export default Detail
