import { trace } from '@opentelemetry/api'
import { NodeSDK } from '@opentelemetry/sdk-node'
import { Resource } from '@opentelemetry/resources'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc'

let sdk: NodeSDK | null = null

export function setupTracer(service: string) {
  if (sdk) return trace.getTracer(service)

  const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT
  sdk = new NodeSDK({
    resource: new Resource({ 'service.name': service }),
    traceExporter: endpoint ? new OTLPTraceExporter({ url: endpoint }) : undefined,
  })
  sdk.start()
  return trace.getTracer(service)
}

export function getTracer(name?: string) {
  return trace.getTracer(name ?? 'default')
}
