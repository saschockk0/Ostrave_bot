type MarqueeProps = {
  items: string[];
  className?: string;
  reverse?: boolean;
};

export function Marquee({ items, className = "", reverse = false }: MarqueeProps) {
  const content = items.join("   ✦   ") + "   ✦   ";
  return (
    <div className={`overflow-hidden ${className}`}>
      <div className={`marquee-track ${reverse ? "reverse" : ""}`}>
        <span className="pr-6">{content}</span>
        <span className="pr-6" aria-hidden="true">
          {content}
        </span>
      </div>
    </div>
  );
}
