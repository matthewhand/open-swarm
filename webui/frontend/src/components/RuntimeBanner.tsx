import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { Alert } from './DaisyUI'
import { fetchRuntimeBanner } from '../lib/api'
import {
  isRuntimeBannerDismissed,
  parseRuntimeBanner,
  saveDismissedRuntimeMode,
  type RuntimeBannerPayload,
  type RuntimeTone,
} from '../lib/runtimeMode'

function alertType(tone: RuntimeTone): 'warning' | 'success' | 'info' {
  if (tone === 'info') return 'success'
  if (tone === 'warning') return 'warning'
  return 'info'
}

function alertClass(tone: RuntimeTone): string {
  if (tone === 'unknown') return 'os-runtime-banner os-runtime-banner--unknown'
  if (tone === 'info') return 'os-runtime-banner os-runtime-banner--isolated'
  return 'os-runtime-banner os-runtime-banner--warning'
}

export default function RuntimeBanner() {
  const query = useQuery({
    queryKey: ['runtime-banner'],
    queryFn: fetchRuntimeBanner,
    retry: 1,
  })
  const banner: RuntimeBannerPayload = query.isError
    ? parseRuntimeBanner(null)
    : parseRuntimeBanner(query.data)
  const [dismissed, setDismissed] = useState(() => isRuntimeBannerDismissed(banner.mode))

  useEffect(() => {
    setDismissed(isRuntimeBannerDismissed(banner.mode))
  }, [banner.mode])

  if (query.isLoading && !query.data) return null
  if (dismissed) return null

  const type = banner.tone === 'unknown' ? 'info' : alertType(banner.tone)

  return (
    <div className="os-runtime-banner-wrap" data-runtime-mode={banner.mode} data-runtime-tone={banner.tone}>
      <Alert type={type} className={alertClass(banner.tone)} role="status">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-medium">{banner.title}</p>
            <p className="mt-0.5 text-sm text-base-content/80">{banner.message}</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-xs btn-square shrink-0"
            aria-label="Dismiss runtime banner"
            onClick={() => {
              saveDismissedRuntimeMode(banner.mode)
              setDismissed(true)
            }}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </Alert>
    </div>
  )
}
