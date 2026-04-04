import React, { ReactNode } from 'react';

/**
 * Card component using DaisyUI classes
 * Docs: https://daisyui.com/components/card/
 */
export interface CardProps {
  children: ReactNode;
  title?: string;
  bordered?: boolean;
  compact?: boolean;
  normal?: boolean;
  side?: boolean;
  imageFull?: boolean;
  className?: string;
  actions?: ReactNode;
}

export const Card = ({
  children,
  title,
  bordered = false,
  compact = false,
  normal = false,
  side = false,
  imageFull = false,
  className = '',
  actions,
}: CardProps) => {
  // Build class list
  const classes = [
    'card',
    bordered ? 'card-bordered' : '',
    compact ? 'card-compact' : '',
    normal ? 'card-normal' : '',
    side ? 'card-side' : '',
    imageFull ? 'image-full' : '',
    className
  ].filter(Boolean);

  return (
    <div className={classes.join(' ')}>
      {title && (
        <div className="card-title p-4 pb-0">
          {title}
        </div>
      )}
      <div className="card-body">
        {children}
      </div>
      {actions && (
        <div className="card-actions justify-end p-4 pt-0">
          {actions}
        </div>
      )}
    </div>
  );
};

/**
 * Card with image support
 */
export interface ImageCardProps extends CardProps {
  imageSrc?: string;
  imageAlt?: string;
}

export const ImageCard = ({
  imageSrc,
  imageAlt = '',
  children,
  ...props
}: ImageCardProps) => {
  return (
    <Card {...props}>
      {imageSrc && (
        <figure>
          <img src={imageSrc} alt={imageAlt} className="w-full h-48 object-cover" />
        </figure>
      )}
      {children}
    </Card>
  );
};

export default Card;
