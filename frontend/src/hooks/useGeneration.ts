import { useCallback, useRef, useState } from 'react'
import { buildWsUrl } from '../api/client'
import type { GenerationStatus, WsMessage } from '../types'

interface UseGenerationOptions {
  onChapterComplete?: (data: WsMessage) => void
}

export function useGeneration(projectId: string, options?: UseGenerationOptions) {
  const [status, setStatus] = useState<GenerationStatus>('idle')
  const [stage, setStage] = useState('')
  const [streamBuffer, setStreamBuffer] = useState('')

  const wsRef = useRef<WebSocket | null>(null)
  const generatingRef = useRef(false)

  const start = useCallback(() => {
    if (generatingRef.current) return

    const ws = new WebSocket(buildWsUrl(projectId))
    wsRef.current = ws
    generatingRef.current = true
    setStatus('generating')
    setStreamBuffer('')
    setStage('正在连接...')

    ws.onopen = () => setStage('初始化中...')

    ws.onmessage = (e: MessageEvent) => {
      const msg: WsMessage = JSON.parse(e.data as string)
      switch (msg.type) {
        case 'stage':
          setStage(msg.message ?? '')
          break
        case 'token':
          setStreamBuffer((prev) => prev + (msg.content ?? ''))
          break
        case 'chapter_complete':
          generatingRef.current = false
          setStatus('idle')
          setStage('')
          options?.onChapterComplete?.(msg)
          break
        case 'error':
          generatingRef.current = false
          setStatus('error')
          setStage(msg.message ?? '未知错误')
          break
      }
    }

    ws.onclose = () => {
      if (generatingRef.current) {
        generatingRef.current = false
        setStatus('idle')
      }
    }

    ws.onerror = () => {
      generatingRef.current = false
      setStatus('error')
      setStage('WebSocket 连接失败，请检查后端是否已启动')
    }
  }, [projectId, options])

  const cancel = useCallback(() => {
    generatingRef.current = false
    wsRef.current?.close()
    setStatus('idle')
    setStage('')
  }, [])

  return { status, stage, streamBuffer, start, cancel }
}
