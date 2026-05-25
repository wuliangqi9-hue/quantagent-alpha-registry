import { type FC } from "react";

type SkeletonVariant = "full" | "compact" | "wide";

type Props = {
  variant?: SkeletonVariant;
  className?: string;
};

const baseCls = "skeleton-panel";

export const SkeletonPanel: FC<Props> = ({ variant = "full", className }) => {
  const cls = [baseCls, `${baseCls}--${variant}`, className].filter(Boolean).join(" ");
  return (
    <section className={cls} aria-busy="true" aria-label="Loading content">
      <div className="skeleton-line skeleton-line--heading" />
      <div className="skeleton-line skeleton-line--body" />
      <div className="skeleton-line skeleton-line--medium" />
      <div className="skeleton-line skeleton-line--short" />
      {variant === "wide" && (
        <>
          <div className="skeleton-line skeleton-line--body" />
          <div className="skeleton-line skeleton-line--medium" />
        </>
      )}
    </section>
  );
};

export const SkeletonGrid: FC = () => (
  <div className="grid skeleton-grid" aria-busy="true" aria-label="Loading dashboard">
    <SkeletonPanel variant="full" />
    <SkeletonPanel variant="compact" />
    <SkeletonPanel variant="compact" />
    <SkeletonPanel variant="wide" />
    <SkeletonPanel variant="full" />
    <SkeletonPanel variant="compact" />
    <SkeletonPanel variant="full" />
    <SkeletonPanel variant="compact" />
    <SkeletonPanel variant="compact" />
    <SkeletonPanel variant="compact" />
  </div>
);