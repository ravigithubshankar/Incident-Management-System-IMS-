import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useIncidents } from '../hooks/useIncidents'
import { useWebSocket } from '../hooks/useWebSocket'
import { Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

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
}

const Dashboard: React.FC = () => {
  const { data: incidents, isLoading, error } = useIncidents()
  const [realTimeIncidents, setRealTimeIncidents] = useState<Incident[]>([])

  // WebSocket for real-time updates
  useWebSocket(
    import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/dashboard`,
    (data) => {
      if (data.type === 'incident_update') {
        setRealTimeIncidents(prev => {
          const existingIndex = prev.findIndex(inc => inc.id === data.incident.id)
          if (existingIndex >= 0) {
            const updated = [...prev]
            updated[existingIndex] = { ...updated[existingIndex], ...data.incident }
            return updated
          }
          return [...prev, data.incident]
        })
      }
    }
  )

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'P0': return 'bg-red-100 text-red-800 border-red-200'
      case 'P1': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'P2': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'P3': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN': return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'INVESTIGATING': return <Clock className="w-4 h-4 text-yellow-500" />
      case 'RESOLVED': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'CLOSED': return <XCircle className="w-4 h-4 text-gray-500" />
      default: return null
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) return `${diffDays}d ago`
    if (diffHours > 0) return `${diffHours}h ago`
    if (diffMins > 0) return `${diffMins}m ago`
    return 'Just now'
  }

  const displayIncidents = incidents || realTimeIncidents

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-600 text-center py-8">
        Error loading incidents: {(error as Error).message}
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Active Incidents</h2>
        <p className="text-gray-600">
          Real-time incident monitoring dashboard
        </p>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Component
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Signals
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {displayIncidents.map((incident) => (
                <tr key={incident.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(incident.severity)}`}>
                      {incident.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {incident.component_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(incident.status)}
                      <span className="text-sm text-gray-900">{incident.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {incident.signal_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {getTimeAgo(incident.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link
                      to={`/incidents/${incident.id}`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {displayIncidents.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No active incidents found
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
