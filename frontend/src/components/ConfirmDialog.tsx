interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ message, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div role="dialog" aria-modal="true">
      <p>{message}</p>
      <button onClick={onCancel}>取消</button>
      <button onClick={onConfirm}>确认删除</button>
    </div>
  );
}
