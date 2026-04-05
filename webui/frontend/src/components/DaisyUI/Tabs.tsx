import React, { useState, ReactNode } from 'react';

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

  return (
    <div className={`tabs ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={`tab ${activeTab === tab.key ? 'tab-active' : ''} ${tab.disabled ? 'tab-disabled' : ''}`}
          onClick={() => !tab.disabled && onChange(tab.key)}
          disabled={tab.disabled}
        >
          {tab.icon && <span className="mr-2">{tab.icon}</span>}
          {tab.label}
        </button>
      ))}
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
  return <div className="tab-content p-4">{children}</div>;
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
export interface AccordionItem {
  key: string;
  title: ReactNode;
  content: ReactNode;
  disabled?: boolean;
  icon?: ReactNode;
}

export interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
  className?: string;
}

export const Accordion = ({
  items,
  allowMultiple = false,
  className = '',
}: AccordionProps) => {
  const [activeItems, setActiveItems] = useState<string[]>([]);

  const toggleItem = (key: string) => {
    if (allowMultiple) {
      setActiveItems(prev =>
        prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
      );
    } else {
      setActiveItems(prev => prev.includes(key) ? [] : [key]);
    }
  };

  return (
    <div className={`join join-vertical w-full ${className}`}>
      {items.map((item) => (
        <div key={item.key} className="collapse collapse-arrow join-item border border-base-300">
          <input
            type="checkbox"
            checked={activeItems.includes(item.key)}
            onChange={() => toggleItem(item.key)}
            disabled={item.disabled}
          />
          <div className="collapse-title font-medium flex items-center gap-2">
            {item.icon && <span>{item.icon}</span>}
            {item.title}
          </div>
          <div className="collapse-content">
            <div className="p-4">
              {item.content}
            </div>
          </div>
        </div>
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
    <div className={`collapse collapse-arrow join-item border border-base-300 ${className}`}>
      <input type="checkbox" defaultChecked={open} disabled={disabled} />
      <div className="collapse-title font-medium flex items-center gap-2">
        {icon && <span>{icon}</span>}
        {title}
      </div>
      <div className="collapse-content">
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>
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
      <div className="text-sm text-gray-500">
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
}: TabsProps) => {
  return (
    <div className={`flex gap-4 ${className}`}>
      <div className="flex flex-col gap-1 min-w-[120px]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`btn btn-sm ${activeTab === tab.key ? 'btn-active' : ''} ${tab.disabled ? 'btn-disabled' : ''}`}
            onClick={() => !tab.disabled && onChange(tab.key)}
            disabled={tab.disabled}
          >
            {tab.icon && <span className="mr-2">{tab.icon}</span>}
            {tab.label}
          </button>
        ))}
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

export default {
  Tabs,
  TabPanel,
  SimpleTabs,
  Accordion,
  AccordionItem,
  Stepper,
  VerticalTabs,
  ContentTabs,
};
