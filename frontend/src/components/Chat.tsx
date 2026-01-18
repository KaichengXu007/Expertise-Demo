import { useState, useRef, useEffect } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Send, Loader2, CheckCircle2, AlertCircle, Upload } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  emailCaptured?: boolean
}

interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
}

interface IngestStatus {
  isLoading: boolean
  message: string
  success: boolean
}

export function Chat(): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState<string>('')
  const [urlInput, setUrlInput] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [ingestStatus, setIngestStatus] = useState<IngestStatus>({
    isLoading: false,
    message: '',
    success: false,
  })
  const [sessionId] = useState<string>(() => `session_${Date.now()}`)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleIngest = async (): Promise<void> => {
    if (!urlInput.trim() || ingestStatus.isLoading) return

    setIngestStatus({
      isLoading: true,
      message: 'Crawling web page and training AI...',
      success: false,
    })

    try {
      const response = await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: urlInput.trim() }),
      })

      const data: ApiResponse = await response.json()

      if (data.success) {
        setIngestStatus({
          isLoading: false,
          message: 'AI training completed, you can start chatting now!',
          success: true,
        })
        setUrlInput('')
        // Clear success message after 3 seconds
        setTimeout(() => {
          setIngestStatus({
            isLoading: false,
            message: '',
            success: false,
          })
        }, 3000)
      } else {
        setIngestStatus({
          isLoading: false,
          message: `Training failed: ${data.message}`,
          success: false,
        })
      }
    } catch (error) {
      setIngestStatus({
        isLoading: false,
        message: `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        success: false,
      })
    }
  }

  const handleSend = async (): Promise<void> => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Create placeholder message for streaming updates
    const assistantMessageId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])

    // Cancel previous request (if any)
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.body) {
        throw new Error('Response body is empty')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'chunk') {
                // Update message content (streaming append)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: msg.content + data.content }
                      : msg
                  )
                )
              } else if (data.type === 'done') {
                // Check if email was captured
                if (data.email_provided) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, emailCaptured: true }
                        : msg
                    )
                  )
                  // Scroll to bottom to show email capture notification
                  setTimeout(() => scrollToBottom(), 100)
                }
              } else if (data.type === 'error') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: `Error: ${data.message}` }
                      : msg
                  )
                )
                break
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was cancelled, do nothing
        return
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
              }
            : msg
        )
      )
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleUrlKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleIngest()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card p-4">
        <h1 className="text-2xl font-bold text-card-foreground">
          Lumina Sales Agent
        </h1>
        <p className="text-sm text-muted-foreground">
          AI-Driven Sales Assistant
        </p>
      </div>

      {/* URL Input Area */}
      <div className="border-b border-border bg-card p-4">
        <div className="flex gap-2 items-center">
          <Input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyPress={handleUrlKeyPress}
            placeholder="Enter web page URL for AI training..."
            disabled={ingestStatus.isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleIngest}
            disabled={ingestStatus.isLoading || !urlInput.trim()}
            size="icon"
          >
            {ingestStatus.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Progress bar and status notification */}
        {ingestStatus.isLoading && (
          <div className="mt-2">
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full animate-pulse" style={{ width: '100%' }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {ingestStatus.message}
            </p>
          </div>
        )}

        {ingestStatus.message && !ingestStatus.isLoading && (
          <div
            className={`mt-2 flex items-center gap-2 p-2 rounded-md ${
              ingestStatus.success
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {ingestStatus.success ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <p className="text-sm">{ingestStatus.message}</p>
          </div>
        )}
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
              <p className="text-lg text-muted-foreground">
                Start chatting with Lumina Sales Agent
              </p>
              <p className="text-sm text-muted-foreground">
                I can help you with sales-related questions
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 relative ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              } ${message.emailCaptured ? 'ring-2 ring-green-500 ring-offset-2' : ''}`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              {message.emailCaptured && (
                <div className="mt-2 flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                  <CheckCircle2 className="h-3 w-3" />
                  <span>Your email information has been automatically saved</span>
                </div>
              )}
              <p className="text-xs opacity-70 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted text-muted-foreground rounded-lg px-4 py-2">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter your message..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            size="icon"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
