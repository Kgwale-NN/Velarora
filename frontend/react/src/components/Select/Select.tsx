import { useContext, useEffect, useRef, useState } from "react";
import { Select as HeroSelect, SelectItem } from "@heroui/select";
import { ChevronDown, Check } from "lucide-react";
import { ThemeContext } from "../../lib/ThemeContext";
import styles from "./Select.module.css";
type Props = {
  label: string;
  options: { value: string | number; label: string }[];
  value?: string | number;
  defaultValue?: string | number;
  onChange?: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  name?: string;
  placeholder?: string;
};
const keyFor = (value: string | number) => "value:" + value;
export function Select({
  label,
  options,
  value,
  defaultValue,
  onChange,
  disabled,
  required,
  name,
  placeholder = "Select an option",
}: Props) {
  const theme = useContext(ThemeContext);
  const host = useRef<HTMLDivElement>(null);
  const [portal, setPortal] = useState<HTMLElement | undefined>();
  useEffect(() => setPortal(host.current?.closest("dialog") ?? undefined), []);
  return (
    <div ref={host} className={styles.host}>
      <HeroSelect
        label={required ? label + " *" : label}
        labelPlacement="outside"
        placeholder={placeholder}
        name={name}
        isDisabled={disabled}
        isRequired={required}
        validationBehavior="native"
        disableAnimation
        selectedKeys={
          value !== undefined
            ? options.some(
                (option) => String(option.value) === String(value),
              ) && !(required && value === "")
              ? [keyFor(value)]
              : []
            : undefined
        }
        defaultSelectedKeys={
          value === undefined
            ? [keyFor(defaultValue ?? options[0]?.value ?? "")]
            : undefined
        }
        onSelectionChange={(keys) => {
          if (keys !== "all") {
            const key = Array.from(keys)[0];
            if (key !== undefined) onChange?.(String(key).slice(6));
          }
        }}
        selectorIcon={<ChevronDown size={16} aria-hidden="true" />}
        classNames={{
          base: styles.field,
          label: styles.label,
          mainWrapper: styles.main,
          trigger: styles.trigger,
          innerWrapper: styles.inner,
          value: styles.value,
          selectorIcon: styles.chevron,
          popoverContent: `${styles.popover} ${theme === "light" ? styles.light : ""}`,
          listboxWrapper: styles.scroll,
          listbox: styles.list,
        }}
        popoverProps={{
          placement: "bottom-start",
          offset: 6,
          portalContainer: portal,
          disableAnimation: true,
          classNames: {
            base: styles.overlay,
            content: `${styles.popover} ${theme === "light" ? styles.light : ""}`,
          },
        }}
        listboxProps={{
          classNames: { base: styles.list, list: styles.items },
          itemClasses: {
            base: styles.option,
            title: styles.optionTitle,
            selectedIcon: styles.selectedIcon,
          },
        }}
      >
        {options.map((option) => (
          <SelectItem
            key={keyFor(option.value)}
            textValue={option.label}
            selectedIcon={<Check size={15} />}
          >
            {option.label}
          </SelectItem>
        ))}
      </HeroSelect>
    </div>
  );
}
