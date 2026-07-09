interface ErrorModalProps {
  message: string | null;
  onDismiss: () => void;
}

export function ErrorModal({ message, onDismiss }: ErrorModalProps) {
  if (!message) return null;
  return (
    <div role="alertdialog" aria-modal="true">
      <p>{message}</p>
      <button onClick={onDismiss}>知道了</button>
    </div>
  );
}
