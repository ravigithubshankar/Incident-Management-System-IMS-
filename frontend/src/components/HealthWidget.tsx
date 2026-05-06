import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface HealthStatus {
  status: string
  postgres: string
  mongo: string
  redis: string
}

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const HealthWidget: React.FC = () => {
  const { data: health, isLoading } = useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/health`)
      if (!response.ok) {
        throw new Error('Health check failed')
      }
      return response.json()
    },
    refetchInterval: 10000, // Poll every 10 seconds
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
        return 'text-green-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-yellow-600'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center space-x-4">
        <div className="animate-pulse">
          <div className="h-5 w-5 bg-gray-300 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center space-x-6">
      <div className="flex items-center space-x-2">
        {getStatusIcon(health?.postgres || 'unknown')}
        <span className={`text-sm font-medium ${getStatusColor(health?.postgres || 'unknown')}`}>
          PostgreSQL
        </span>
      </div>
      <div className="flex items-center space-x-2">
        {getStatusIcon(health?.mongo || 'unknown')}
        <span className={`text-sm font-medium ${getStatusColor(health?.mongo || 'unknown')}`}>
          MongoDB
        </span>
      </div>
      <div className="flex items-center space-x-2">
        {getStatusIcon(health?.redis || 'unknown')}
        <span className={`text-sm font-medium ${getStatusColor(health?.redis || 'unknown')}`}>
          Redis
        </span>
      </div>
    </div>
  )
}

export default HealthWidget
