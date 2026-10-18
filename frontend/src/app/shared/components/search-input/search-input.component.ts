import { Component, input, model, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideSearch, LucideX } from '@lucide/angular';

@Component({
  selector: 'app-search-input',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideSearch, LucideX],
  templateUrl: './search-input.component.html',
  styleUrl: './search-input.component.scss'
})
export class SearchInputComponent {
  /** Two-way bindable search value */
  value = model<string>('');

  /** Input placeholder */
  placeholder = input<string>('Nhập từ khóa...');

  /** Optional label above the input */
  label = input<string>('');

  /** Whether to show a clear button when input has text */
  showClear = input<boolean>(true);

  /** Emits when search term changes */
  search = output<string>();

  onValueChange(val: string): void {
    this.value.set(val);
    this.search.emit(val);
  }

  onClear(): void {
    this.value.set('');
    this.search.emit('');
  }
}
