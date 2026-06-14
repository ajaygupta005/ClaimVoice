import VoiceAssistantUI from '@/components/VoiceAssistantUI'

// Break out of the default max-w-5xl shell so the voice cockpit uses full width.
export default function VoicePage() {
  return (
    <div className="-mx-8 px-6">
      <VoiceAssistantUI />
    </div>
  )
}
