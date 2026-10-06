import './ui.css';

export function PageCard({ as: Container = 'div', className = '', children, ...props }) {
  return <Container className={`ng-ui ng-page-card ${className}`} {...props}>{children}</Container>;
}

export function PageHeader({ context, title, description, titleId, icon: Icon, children }) {
  return (
    <header className="ng-page-header">
      <span className="ng-page-header__context">
        {Icon && <Icon size={16} aria-hidden="true" />}{context}
      </span>
      <h1 id={titleId}>{title}</h1>
      <p className="ng-page-header__description">{description}</p>
      {children}
    </header>
  );
}

export function ActionBar({ children }) {
  return <div className="ng-action-bar">{children}</div>;
}
