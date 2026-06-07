interface Props {
  width?: string;
  height?: string;
  count?: number;
}

export default function Skeleton({ width = '100%', height = '20px', count = 1 }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" style={{ width, height }} />
      ))}
    </div>
  );
}
