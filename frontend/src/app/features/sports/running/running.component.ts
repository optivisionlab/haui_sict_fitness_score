import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-running',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './running.component.html',
  styleUrl: './running.component.scss'
})
export class RunningComponent {
  @Output() navigate = new EventEmitter<void>();

  onNavigate() {
    this.navigate.emit();
  }
}
