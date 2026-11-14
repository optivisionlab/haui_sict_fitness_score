import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Pickleball } from './pickleball.component';

describe('Pickleball', () => {
  let component: Pickleball;
  let fixture: ComponentFixture<Pickleball>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Pickleball],
    }).compileComponents();

    fixture = TestBed.createComponent(Pickleball);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
