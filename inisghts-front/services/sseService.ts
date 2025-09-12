import { useToast } from 'vue-toastification';

let eventSourceInstance: EventSource | null = null;

// Note: useToast() is a composable. It's generally called inside a component's setup()
// or another composable. We'll call it inside the `connect` method, which itself
// will be invoked from a component context, ensuring `useToast` works as expected.

export const sseService = {
  connect: (
    params: { 
      taskIds?: string[]; // For report generation tasks
      jobIds?: string[];  // For scraping jobs
    },
    onOpen?: () => void,
    onMessage?: (data: any) => void, // Callback for generic messages
    onError?: (error: Event) => void,
    onClose?: (event_id: string | null) => void // Callback when a specific task/job stream ends or general close
  ) => {
    const toast = useToast();

    if (eventSourceInstance) {
      console.log("SSE: Closing existing EventSource connection.");
      eventSourceInstance.close();
      eventSourceInstance = null;
    }

    const queryParams = new URLSearchParams();
    if (params.taskIds && params.taskIds.length > 0) {
      queryParams.append('subscribe_task_ids', params.taskIds.join(','));
    }
    if (params.jobIds && params.jobIds.length > 0) {
      queryParams.append('subscribe_job_ids', params.jobIds.join(','));
    }

    if (queryParams.toString() === "") {
      console.error("SSE: No taskIds or jobIds provided for connection.");
      toast.error("Cannot connect to status updates without specifying a task or job.");
      return;
    }

    const sseUrl = `/api/sse/stream?${queryParams.toString()}`;
    console.log(`SSE: Connecting to ${sseUrl}`);
    eventSourceInstance = new EventSource(sseUrl);

    const subscribedIds = [...(params.taskIds || []), ...(params.jobIds || [])];
    const firstId = subscribedIds.length > 0 ? subscribedIds[0] : 'generic';

    // Initial toast (optional, or make it more generic)
    // toast.info(`Connecting to status updates for: ${subscribedIds.join(', ').substring(0, 50)}...`);

    eventSourceInstance.onopen = () => {
      console.log(`SSE: Connection opened successfully for subscriptions: ${subscribedIds.join(', ')}`);
      if (onOpen) onOpen();
      // A generic "listening" toast can be good.
      toast.info(`Listening for updates... (IDs: ${subscribedIds.map(id => id.substring(0,8)).join(', ')})`);
    };

    eventSourceInstance.onmessage = (event: MessageEvent) => {
      try {
        const parsedEvent = JSON.parse(event.data);
        console.log("SSE: Message received:", parsedEvent);

        // Extract the core data, event_group, and specific event_id (task_id or job_id)
        const { event_group, id: event_specific_id, data: eventPayload } = parsedEvent;

        if (onMessage) {
          onMessage(parsedEvent); // Pass the full parsed event to the generic callback
        }

        // Handle specific event groups and statuses for toasts
        if (event_group === "system" && eventPayload.status === "connected") {
          // Already handled by onopen or a generic toast
          console.log(`SSE System: ${eventPayload.message}`);
          return; // No toast needed here, usually
        }
        
        // Default message prefix
        let messagePrefix = `Update (${(event_specific_id || 'general').substring(0,8)})`;
        if (event_group === "report_generation") messagePrefix = `Report Gen. (${(event_specific_id || 'task').substring(0,8)})`;
        if (event_group === "scrape_tracking") messagePrefix = `Scraping (${(event_specific_id || 'job').substring(0,8)})`;


        if (eventPayload.status === "completed") {
          toast.success(`${messagePrefix}: ${eventPayload.message || 'Completed successfully!'}`);
          if (eventPayload.task_id && onClose) onClose(eventPayload.task_id); // Notify about specific task completion
          // Do not close the main EventSource if it's subscribed to multiple event_ids,
          // unless this is the very last event_id it was interested in.
          // The backend will keep sending heartbeats. The client decides when to close based on its needs.

        } else if (eventPayload.status === "failed" || eventPayload.status === "error" || eventPayload.status === "timeout" || eventPayload.status === "generation_error" || eventPayload.status === "archetype_error" || eventPayload.status === "save_error") {
          toast.error(`${messagePrefix}: ${eventPayload.message || eventPayload.error || 'An error occurred.'}`);
          if (eventPayload.task_id && onClose) onClose(eventPayload.task_id); // Notify about specific task failure
          // Similar to 'completed', don't close prematurely for multi-subscriptions.

        } else if (eventPayload.status) { // For other intermediate statuses
          toast.info(`${messagePrefix}: ${eventPayload.message || eventPayload.status}`);
        }

      } catch (e) {
        console.error("SSE: Error parsing message data or handling message:", e, "Raw data:", event.data);
        toast.error("Received an invalid status update.");
      }
    };

    eventSourceInstance.onerror = (error: Event) => {
      console.error(`SSE: Error for subscriptions ${subscribedIds.join(', ')}:`, error);
      if (onError) onError(error);

      if (eventSourceInstance && eventSourceInstance.readyState === EventSource.CLOSED) {
        toast.error("Connection to status updates lost. Please refresh or try again later.");
        if (onClose) onClose(null); // General close notification
        eventSourceInstance = null; 
      } else {
        // EventSource might be retrying.
        console.warn("SSE: Connection error. EventSource may attempt to reconnect.");
        // Avoid toast here as it might be a temporary network blip and EventSource handles retries.
      }
    };
  },

  disconnect: () => {
    if (eventSourceInstance) {
      console.log("SSE: Connection explicitly disconnected by client.");
      eventSourceInstance.close();
      eventSourceInstance = null;
      // No toast here generally, as it's an explicit action.
    }
  },
};
