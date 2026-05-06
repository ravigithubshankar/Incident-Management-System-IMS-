import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

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

interface StatusUpdateRequest {
  status: string
}

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export const useIncidents = () => {
  return useQuery<Incident[]>({
    queryKey: ['incidents'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/v1/incidents`, {
        headers: {
          'X-API-Key': 'dev-api-key-12345'
        }
      })
      if (!response.ok) {
        throw new Error('Failed to fetch incidents')
      }
      return response.json()
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

export const useIncident = (id: string) => {
  return useQuery<Incident & { signals: any[], rca?: any }>({
    queryKey: ['incident', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/api/v1/incidents/${id}`, {
        headers: {
          'X-API-Key': 'dev-api-key-12345'
        }
      })
      if (!response.ok) {
        throw new Error('Failed to fetch incident')
      }
      return response.json()
    },
    enabled: !!id
  })
}

export const useUpdateIncidentStatus = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const response = await fetch(`${API_BASE}/api/v1/incidents/${id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'dev-api-key-12345'
        },
        body: JSON.stringify({ status })
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || 'Failed to update status')
      }

      return response.json()
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      queryClient.invalidateQueries({ queryKey: ['incident', variables.id] })
    }
  })
}
