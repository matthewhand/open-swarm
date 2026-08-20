import { useState, useRef, ReactNode } from 'react';

/**
 * Tab interface
 */
export interface Tab {
  key: string;
  label: ReactNode;
  disabled?: boolean;
  icon?: ReactNode;
}

/**
 * Tabs component props
 */
export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabKey: string) => void;
  variant?: 'boxed' | 'lifted' | 'bordered';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Tabs component
 * Docs: https://daisyui.com/components/tabs/
 */
export const Tabs = ({
  tabs,
  activeTab,
  onChange,
  variant = 'boxed',
  size = 'md',
  className = '',
}: TabsProps) => {
  const variantClasses = {
    boxed: 'tabs-boxed',
    lifted: 'tabs-lifted',
    bordered: 'tabs-bordered',
  };

  const sizeClasses = {
    sm: 'tabs-sm',
    md: 'tabs-md',
    lg: 'tabs-lg',
  };

  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let newIndex = index;
    let step = 0;

    if (e.key === 'ArrowRight') {
      newIndex = index + 1 >= tabs.length ? 0 : index + 1;
      step = 1;
    } else if (e.key === 'ArrowLeft') {
      newIndex = index - 1 < 0 ? tabs.length - 1 : index - 1;
      step = -1;
    } else if (e.key === 'Home') {
      newIndex = 0;
      step = 1;
    } else if (e.key === 'End') {
      newIndex = tabs.length - 1;
      step = -1;
    }

    if (step !== 0 && newIndex !== index) {
      e.preventDefault();
      let count = 0;
      while (tabs[newIndex].disabled && count < tabs.length) {
        newIndex = step === 1
          ? (newIndex + 1 >= tabs.length ? 0 : newIndex + 1)
          : (newIndex - 1 < 0 ? tabs.length - 1 : newIndex - 1);
        count++;
      }

      if (!tabs[newIndex].disabled) {
        onChange(tabs[newIndex].key);
        const tabElement = tabRefs.current[newIndex];
        if (tabElement) {
          tabElement.focus();
        }
      }
    }
  };

  return (
    <div
      className={`tabs ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      role="tablist"
      aria-orientation="horizontal"
    >
      {tabs.map((tab, index) => {
        const isSelected = activeTab === tab.key;
        return (
          <button
            ref={(el) => (tabRefs.current[index] = el)}
            id={`tab-${tab.key}`}
            key={tab.key}
            role="tab"
            aria-selected={isSelected}
            aria-controls={`panel-${tab.key}`}
            tabIndex={isSelected ? 0 : -1}
            className={`tab ${isSelected ? 'tab-active' : ''} ${tab.disabled ? 'tab-disabled' : ''}`}
            onClick={() => !tab.disabled && onChange(tab.key)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            disabled={tab.disabled}
          >
            {tab.icon && <span className="mr-2" aria-hidden="true">{tab.icon}</span>}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};

/**
 * Tab Panel component
 */
export interface TabPanelProps {
  activeTab: string;
  tabKey: string;
  children: ReactNode;
}

export const TabPanel = ({ activeTab, tabKey, children }: TabPanelProps) => {
  if (activeTab !== tabKey) return null;
  return (
    <div
      id={`panel-${tabKey}`}
      role="tabpanel"
      aria-labelledby={`tab-${tabKey}`}
      tabIndex={0}
      className="tab-content p-4"
    >
      {children}
    </div>
  );
};

/**
 * Simple Tabs component with built-in state management
 */
export const SimpleTabs = ({
  tabs,
  children,
  variant = 'boxed',
  size = 'md',
  className = '',
}: {
  tabs: Tab[];
  children: ReactNode;
  variant?: 'boxed' | 'lifted' | 'bordered';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) => {
  const [activeTab, setActiveTab] = useState(tabs[0]?.key || '');

  return (
    <>
      <Tabs
        tabs={tabs}
        activeTab={activeTab}
        onChange={setActiveTab}
        variant={variant}
        size={size}
        className={className}
      />
      {children}
    </>
  );
};

/**
 * Accordion component
 * Docs: https://daisyui.com/components/accordion/
 */
export interface AccordionItemType {
  key: string;
  title: ReactNode;
  content: ReactNode;
  disabled?: boolean;
  icon?: ReactNode;
}

export interface AccordionProps {
  items: AccordionItemType[];
  allowMultiple?: boolean;
  className?: string;
}

export const Accordion = ({
  items,
  allowMultiple = false,
  className = '',
}: AccordionProps) => {
  const [activeItems, setActiveItems] = useState<string[]>([]);

  const toggleItem = (e: React.SyntheticEvent<HTMLDetailsElement>, key: string) => {
    const isOpen = e.currentTarget.open;
    if (allowMultiple) {
      setActiveItems(prev =>
        isOpen ? [...new Set([...prev, key])] : prev.filter(k => k !== key)
      );
    } else {
      if (isOpen) {
        setActiveItems([key]);
      } else {
        setActiveItems(prev => prev.filter(k => k !== key));
      }
    }
  };

  return (
    <div className={`join join-vertical w-full ${className}`}>
      {items.map((item) => (
        <details
          key={item.key}
          className="collapse collapse-arrow join-item border border-base-300"
          open={activeItems.includes(item.key)}
          onToggle={(e) => toggleItem(e, item.key)}
        >
          <summary
            className="collapse-title font-medium flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden"
            tabIndex={item.disabled ? -1 : 0}
            onClick={(e) => {
              if (item.disabled) e.preventDefault();
            }}
          >
            {item.icon && <span aria-hidden="true">{item.icon}</span>}
            {item.title}
          </summary>
          <div className="collapse-content">
            <div className="p-4">
              {item.content}
            </div>
          </div>
        </details>
      ))}
    </div>
  );
};

/**
 * Accordion Item component (for uncontrolled usage)
 */
export interface AccordionItemProps {
  title: ReactNode;
  children: ReactNode;
  open?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  className?: string;
}

export const AccordionItem = ({
  title,
  children,
  open = false,
  disabled = false,
  icon,
  className = '',
}: AccordionItemProps) => {
  return (
    <details
      className={`collapse collapse-arrow join-item border border-base-300 ${className}`}
      open={open}
    >
      <summary
        className="collapse-title font-medium flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden"
        tabIndex={disabled ? -1 : 0}
        onClick={(e) => {
          if (disabled) e.preventDefault();
        }}
      >
        {icon && <span aria-hidden="true">{icon}</span>}
        {title}
      </summary>
      <div className="collapse-content">
        <div className="p-4">
          {children}
        </div>
      </div>
    </details>
  );
};

/**
 * Stepper/Tabs combination for multi-step forms
 */
export interface StepperProps {
  steps: Tab[];
  activeStep: number;
  onStepChange: (stepIndex: number) => void;
  className?: string;
}

export const Stepper = ({
  steps,
  activeStep,
  onStepChange,
  className = '',
}: StepperProps) => {
  return (
    <div className={`flex items-center justify-between mb-8 ${className}`}>
      <div className="flex items-center gap-4">
        {steps.map((step, index) => (
          <button
            key={step.key}
            className={`btn btn-sm ${activeStep === index ? 'btn-primary' : 'btn-ghost'} ${activeStep > index ? 'btn-success' : ''}`}
            onClick={() => onStepChange(index)}
            disabled={activeStep < index}
          >
            {step.icon && <span className="mr-1">{step.icon}</span>}
            {step.label}
          </button>
        ))}
      </div>
      <div className="text-sm text-base-content/70">
        Step {activeStep + 1} of {steps.length}
      </div>
    </div>
  );
};

/**
 * Vertical Tabs component
 */
export const VerticalTabs = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}: Omit<TabsProps, 'tabs'> & { tabs: ContentTab[] }) => {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let newIndex = index;
    let step = 0;

    if (e.key === 'ArrowDown') {
      newIndex = index + 1 >= tabs.length ? 0 : index + 1;
      step = 1;
    } else if (e.key === 'ArrowUp') {
      newIndex = index - 1 < 0 ? tabs.length - 1 : index - 1;
      step = -1;
    } else if (e.key === 'Home') {
      newIndex = 0;
      step = 1;
    } else if (e.key === 'End') {
      newIndex = tabs.length - 1;
      step = -1;
    }

    if (step !== 0 && newIndex !== index) {
      e.preventDefault();
      let count = 0;
      while (tabs[newIndex].disabled && count < tabs.length) {
        newIndex = step === 1
          ? (newIndex + 1 >= tabs.length ? 0 : newIndex + 1)
          : (newIndex - 1 < 0 ? tabs.length - 1 : newIndex - 1);
        count++;
      }

      if (!tabs[newIndex].disabled) {
        onChange(tabs[newIndex].key);
        tabRefs.current[newIndex]?.focus();
      }
    }
  };

  return (
    <div className={`flex gap-4 ${className}`}>
      <div
        className="flex flex-col gap-1 min-w-[120px]"
        role="tablist"
        aria-orientation="vertical"
      >
        {tabs.map((tab, index) => {
          const isSelected = activeTab === tab.key;
          return (
            <button
              ref={(el) => { tabRefs.current[index] = el; }}
              id={`tab-${tab.key}`}
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-controls={`panel-${tab.key}`}
              tabIndex={isSelected ? 0 : -1}
              className={`btn btn-sm ${isSelected ? 'btn-active' : ''} ${tab.disabled ? 'btn-disabled' : ''}`}
              onClick={() => !tab.disabled && onChange(tab.key)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              disabled={tab.disabled}
            >
              {tab.icon && <span className="mr-2" aria-hidden="true">{tab.icon}</span>}
              {tab.label}
            </button>
          );
        })}
      </div>
      <div className="flex-1">
        {tabs.map((tab) => (
          <TabPanel key={tab.key} activeTab={activeTab} tabKey={tab.key}>
            {tab.content}
          </TabPanel>
        ))}
      </div>
    </div>
  );
};

/**
 * Enhanced Tabs with content
 */
export interface ContentTab extends Tab {
  content: ReactNode;
}

export const ContentTabs = ({
  tabs,
  activeTab,
  onChange,
  variant = 'boxed',
  size = 'md',
  className = '',
}: {
  tabs: ContentTab[];
  activeTab: string;
  onChange: (tabKey: string) => void;
  variant?: 'boxed' | 'lifted' | 'bordered';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) => {
  return (
    <div className={className}>
      <Tabs
        tabs={tabs}
        activeTab={activeTab}
        onChange={onChange}
        variant={variant}
        size={size}
      />
      <div className="mt-4">
        {tabs.map((tab) => (
          <TabPanel key={tab.key} activeTab={activeTab} tabKey={tab.key}>
            {tab.content}
          </TabPanel>
        ))}
      </div>
    </div>
  );
};

const TabsComponents = {
  Tabs,
  TabPanel,
  SimpleTabs,
  Accordion,
  AccordionItem,
  Stepper,
  VerticalTabs,
  ContentTabs,
};

export default TabsComponents;
