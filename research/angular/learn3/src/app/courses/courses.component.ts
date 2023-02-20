// Custom property binding between components
import { Component } from '@angular/core';

@Component({
  selector: 'app-courses',
  templateUrl: './courses.component.html',
  styleUrls: ['./courses.component.css']
})
export class CoursesComponent {

  courses = [
    {
      id: 101, name:'blabla1', type: 'free'
    },
    {
      id: 102, name:'blabla2', type: 'free'
    },
    {
      id: 103, name:'blabla10', type: 'premium'
    },
    {
      id: 103, name:'blabla11', type: 'premium'
    },
    {
      id: 104, name:'blabla12', type: 'premium'
    }
  ]

  getTotal() {
    return this.courses.length;
  }

  getTotalFree() {
    return this.courses.filter(course => course.type === 'free').length;
  }

  getTotalPremium() {
    return this.courses.filter(course => course.type === 'premium').length;
  }

  childRadioState: string = 'all'

  //Change the filter variable
  onFilterChangeEvent(data: string){
    this.childRadioState = data;
    console.log("I got an event from the child filter - " + this.childRadioState)
  }

}
