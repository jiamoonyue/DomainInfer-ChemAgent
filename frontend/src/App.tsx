import { useState, useRef, useEffect } from 'react'
import { Send, Plus, Trash2, Loader2, Atom } from 'lucide-react'

interface Message {
  role: string
  content: string
  type?: string
}

interface Conversation {
  id: string
  title: string
}

const API = 'http://127.0.0.1:8000'

export default function App() {
  const [convs, setConvs] = useState<Conversation[]>([])
  const [activeConv, setActiveConv] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatRef = useRef<HTMLDivElement>(null)
  const aborterRef = useRef<AbortController | null>(null)

  useEffect(() => {
    fetch(`${API}/api/conversations`).then(r => r.json()).then(setConvs).catch(() => {})
  }, [])

  useEffect(() => {
    chatRef.current?.scrollTo(0, chatRef.current.scrollHeight)
  }, [messages])

  const newChat = async () => {
    try {
      const r = await fetch(`${API}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat' }),
      })
      const c: Conversation = await r.json()
      setConvs(prev => [c, ...prev])
      setActiveConv(c.id)
      setMessages([])
    } catch { /* offline */ }
  }

  const selectChat = async (id: string) => {
    setActiveConv(id)
    try {
      const r = await fetch(`${API}/api/conversations/${id}`)
      const c = await r.json()
      setMessages(c.messages || [])
    } catch { setMessages([]) }
  }

  const deleteChat = (id: string) => {
    fetch(`${API}/api/conversations/${id}`, { method: 'DELETE' })
    setConvs(prev => prev.filter(c => c.id !== id))
    if (activeConv === id) { setActiveConv(null); setMessages([]) }
  }

  const send = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])

    if (!activeConv) {
      try {
        const r = await fetch(`${API}/api/conversations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: userMsg.slice(0, 40) }),
        })
        const c: Conversation = await r.json()
        setActiveConv(c.id)
        setConvs(prev => [c, ...prev])
      } catch { /* continue without conv */ }
    }

    setLoading(true)
    setMessages(prev => [...prev, { role: 'assistant', content: '', type: 'streaming' }])
    aborterRef.current = new AbortController()

    try {
      const resp = await fetch(`${API}/api/agents/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: userMsg }],
          temperature: 0.7,
          max_tokens: 500,
        }),
        signal: aborterRef.current.signal,
      })

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let full = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()!
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const d = JSON.parse(line.slice(6))
            if (d.event === 'token' && d.content) {
              full += d.content
              setMessages(prev => {
                const next = [...prev]
                const last = next[next.length - 1]
                if (last?.type === 'streaming') last.content = full
                return next
              })
            } else if (d.event === 'tool_result') {
              setMessages(prev => [...prev, {
                role: 'tool',
                content: d.tool + ': ' + String(d.result || '').slice(0, 100),
                type: 'tool',
              }])
            }
          } catch { /* skip */ }
        }
      }

      setMessages(prev => prev.map(m => m.type === 'streaming' ? { ...m, type: 'done' } : m))
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setMessages(prev => [...prev, { role: 'system', content: 'Error: ' + err.message }])
      }
    }

    setLoading(false)
    aborterRef.current = null
    fetch(`${API}/api/conversations`).then(r => r.json()).then(setConvs).catch(() => {})
  }

  const stop = () => {
    aborterRef.current?.abort()
    setLoading(false)
  }

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <div className="w-64 bg-gray-50 border-r flex flex-col flex-shrink-0">
        <div className="p-4 border-b">
          <h1 className="text-lg font-bold flex items-center gap-2">
            <Atom className="w-5 h-5 text-blue-600" /> AgentForge
          </h1>
          <p className="text-xs text-gray-400 mt-1">Enterprise AI Platform</p>
        </div>
        <button
          onClick={newChat}
          className="m-3 flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" /> New Chat
        </button>
        <div className="flex-1 overflow-y-auto px-2">
          {convs.map(c => (
            <div
              key={c.id}
              onClick={() => selectChat(c.id)}
              className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm mb-0.5 group ${
                activeConv === c.id ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              <span className="truncate">{c.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); deleteChat(c.id) }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded"
              >
                <Trash2 className="w-3 h-3 text-red-500" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <div ref={chatRef} className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Atom className="w-16 h-16 mb-4 text-blue-200" />
              <h2 className="text-xl font-semibold text-gray-600 mb-2">AgentForge</h2>
              <p className="text-sm">Start a conversation with the AI Agent</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.type === 'tool' ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-sm text-green-800 max-w-md">
                      <span className="font-medium">&#128736; Tool:</span> {m.content}
                    </div>
                  ) : m.role === 'system' ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">
                      {m.content}
                    </div>
                  ) : m.role === 'user' ? (
                    <div className="bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 max-w-md text-sm">
                      {m.content}
                    </div>
                  ) : (
                    <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-2.5 max-w-2xl text-sm leading-relaxed">
                      {m.content || (m.type === 'streaming' ? (
                        <span className="flex items-center gap-2 text-gray-400">
                          <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
                        </span>
                      ) : '')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <div className="max-w-3xl mx-auto flex gap-3">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Send a message..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
            />
            {loading ? (
              <button onClick={stop} className="px-4 py-2 bg-red-500 text-white rounded-xl text-sm hover:bg-red-600">
                Stop
              </button>
            ) : (
              <button
                onClick={send}
                disabled={!input.trim()}
                className="px-3 py-2 bg-blue-600 text-white rounded-xl disabled:opacity-40 hover:bg-blue-700"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
