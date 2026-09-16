import {
  Component,
  ElementRef,
  HostListener,
  computed,
  input,
  model,
  output,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideChevronDown, LucideCheck } from '@lucide/angular';

export interface SelectOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-select',
  standalone: true,
  imports: [CommonModule, LucideChevronDown, LucideCheck],
  templateUrl: './select.component.html',
  styleUrl: './select.component.scss'
})
export class SelectComponent {
  /** Optional label above the select */
  label = input<string>('');

  /** List of selectable options */
  options = input<SelectOption[]>([]);

  /** Selected value (two-way bindable) */
  value = model<string>('');

  /** Placeholder when no value selected */
  placeholder = input<string>('Chọn...');

  /** Emits whenever value changes */
  change = output<string>();

  /** Dropdown open state */
  isOpen = signal<boolean>(false);

  /** Currently selected option object */
  selectedOption = computed(() => {
    return this.options().find((opt) => opt.value === this.value()) || null;
  });

  /** Display label in the trigger box */
  displayLabel = computed(() => {
    return this.selectedOption()?.label || this.placeholder();
  });

  constructor(private elementRef: ElementRef) {}

  toggleDropdown(): void {
    this.isOpen.set(!this.isOpen());
  }

  selectOption(opt: SelectOption): void {
    this.value.set(opt.value);
    this.change.emit(opt.value);
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
    }
  }
}
