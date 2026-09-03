import { memo } from 'react'
import { Search, X } from 'lucide-react'

interface SearchBarProps {
  value: string
  onChange: (query: string) => void
  onOpen?: () => void
}

export const SearchBar = memo(function SearchBar({ value, onChange, onOpen }: SearchBarProps) {
  return (
    <div className="px-3 py-2">
      <label className="relative block">
        <span className="sr-only">Search agents</span>
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-base-content/40" />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => onOpen?.()}
          onClick={() => onOpen?.()}
          placeholder="Search…"
          className="input input-sm input-bordered w-full pl-8 pr-8"
        />
        {value ? (
          <button
            type="button"
            title="Clear search"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 btn btn-ghost btn-xs btn-circle"
            onClick={() => onChange('')}
          >
            <X className="w-3 h-3" />
          </button>
        ) : null}
      </label>
    </div>
  )
})
