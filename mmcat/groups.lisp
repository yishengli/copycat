(defflavor group
    (group-category ; E.g., "succgrp" or "predgrp".
     (direction-category nil) ; E.g., "left" or "right".
     left-obj right-obj (middle-obj nil) ; The left, right, and middle (if any)
                                         ; objects in this group.
     left-obj-position right-obj-position ; The string-positions of the left 
                                          ; and right objects in this group.
     object-list ; A list of the objects in this group.
     bond-list ; A list of the bonds in this group.
     bond-category ; The bond category associated with the 
                       ; group-category (e.g., "successor" is associated with
                       ; "succgrp").
     (bond-facet nil) ; The description-type upon which the bonds making up
                         ; this group are based (i.e., letter-category or
                         ; length).
     (bond-descriptions nil) ; Descriptions involving the bonds 
                                 ;  making up the group.  These are separated 
				 ; from other descriptions since they are not 
				 ; always used in the same way.

(defun make-group (string group-category direction-category 
	           left-obj right-obj object-list bond-list 
		   &aux new-group new-group-letter-category 
			length-description-probability new-bond-facet)
; Returns a new group.
  (setq new-group
       (make-instance 'group 
         :string string
         :left-string-position (send left-obj :left-string-position)
         :right-string-position (send right-obj :right-string-position)
	 :structure-category 'group 
         :group-category group-category 
         :direction-category direction-category
         :left-obj left-obj
	 :right-obj right-obj
	 :middle-obj (loop for obj in object-list 
	                   when (eq (send obj :get-descriptor 
					  plato-string-position-category) 
				    plato-middle) 
	                   return obj)
         :left-obj-position (send left-obj :left-string-position)
         :right-obj-position (send right-obj :right-string-position)
	 :object-list object-list
         :bond-list bond-list
	 :bond-category (send group-category 
			      :get-related-node plato-bond-category)))

  ; Add some descriptions to the new group.
  
  ; Add object-category description and string-position description (if any).
  (if* (send new-group :spans-whole-string?)
   then (send new-group :add-description 
	      (make-description new-group plato-string-position-category 
		                plato-whole)))
  (send new-group :add-description 
	(make-description new-group plato-object-category plato-group))

  (cond ((and (send new-group :leftmost-in-string?) 
	      (not (send new-group :spans-whole-string?)))
         (send new-group :add-description 
	       (make-description new-group plato-string-position-category 
		                 plato-leftmost)))
        ((send new-group :middle-in-string?) 
         (send new-group :add-description 
	       (make-description new-group plato-string-position-category 
		                 plato-middle)))
        ((and (send new-group :rightmost-in-string?) 
              (not (send new-group :spans-whole-string?)))
         (send new-group :add-description 
               (make-description new-group plato-string-position-category 
		                 plato-rightmost))))

  ; If new-group is an samegrp based on letter-category, then give it a
  ; letter-category description.
  (if* (and (eq group-category plato-samegrp) 
	    (or (null bond-list)
	        (eq (send (car bond-list) :bond-facet)
		    plato-letter-category)))
   then (setq new-group-letter-category 
	      (send (send new-group :left-obj) :get-descriptor 
		    plato-letter-category))
        (send new-group :add-description 
	      (make-description new-group plato-letter-category 
		                new-group-letter-category))
	(send new-group :set-pname 
	      (send new-group-letter-category :pname)))

  ; Add group-category, direction-category, and bond descriptions.
  (send new-group :add-description 
	(make-description new-group plato-group-category group-category))
  (if* (send new-group :direction-category)
   then (send new-group :add-description 
	      (make-description new-group plato-direction-category 
 		                (send new-group :direction-category))))
  
  ; Add some descriptions of the bonds making up the group to the 
  ; group's bond-descriptions.
  ; The bond-facet is either letter-category or length.
  ; This assumes that all bonds in the group are based on the same facet.
  (if* (send new-group :bond-list)
   then (setq new-bond-facet 
	      (send (car (send new-group :bond-list)) :bond-facet))
        (send new-group :set-bond-facet new-bond-facet)
        (send new-group :add-bond-description 
	      (make-description new-group plato-bond-facet 
		                new-bond-facet)))
 
  (send new-group :add-bond-description 
	(make-description new-group plato-bond-category
	                  (send new-group :bond-category)))
 
  ; Decide whether or not to add a length description to the group.
  ; Only length descriptions from 1 to 5 can be added to groups.  This
  ; is not very general and should eventually be fixed.
  (setq length-description-probability 
        (send new-group :length-description-probability))

  (if* (eq (flip-coin length-description-probability) 'heads)
   then  
        (send new-group :add-description
	      (make-description new-group plato-length
		                (get-plato-number (send new-group :length))))
  new-group)

(defun in-group? (obj1 obj2)
; Returns t if the two objects are in a group.
 (and (send obj1 :group) (eq (send obj1 :group) (send obj2 :group))))

;---------------------------------------------
; subgroup? | Group.is_subgroup_of
;---------------------------------------------

;---------------------------------------------
; overlaps? | Group.overlaps
;---------------------------------------------

;---------------------------------------------
; get-incompatible-groups
;---------------------------------------------

;---------------------------------------------
; get-incompatible-correspondences
;---------------------------------------------

(defmethod (group :incompatible-correspondence?) 
           (c obj &aux string-position-category-concept-mapping other-obj
		    other-bond group-concept-mapping)
; Returns t if the given correspondence is incompatible with the given group.
(block nil
  (setq string-position-category-concept-mapping
        (loop for cm in (send c :concept-mapping-list)
              when (eq (send cm :description-type1) plato-string-position-category)
	      return cm))

  (if* (null string-position-category-concept-mapping)
   then (return nil))
  (setq other-obj (send c :other-obj obj))
  (if* (send other-obj :leftmost-in-string?)
   then (setq other-bond (send other-obj :right-bond))
   else (if* (send other-obj :rightmost-in-string?)
	 then (setq other-bond (send other-obj :left-bond))))
  (if* (or (null other-bond) 
	   (null (send other-bond :direction-category))) 
   then (return nil))
  (setq group-concept-mapping
        (make-concept-mapping 
	    plato-direction-category plato-direction-category
 	    direction-category (send other-bond :direction-category)
	    nil nil))
  (if* (incompatible-concept-mappings? 
	   group-concept-mapping string-position-category-concept-mapping)
   then t)))

;---------------------------------------------
; group.get-bonds-to-be-flipped | Group.get_bonds_to_be_flipped
;---------------------------------------------

;---------------------------------------------
; spans-whole-string?
;---------------------------------------------

;---------------------------------------------
; proposed?
;---------------------------------------------

;---------------------------------------------
; propose-group | Workspace.propose_group
;---------------------------------------------
  
;---------------------------------------------
; single-letter-group-probability
;---------------------------------------------

;---------------------------------------------
; length-description-probability
;---------------------------------------------

;----------------------------------------------
; group.print | REMOVED
;---------------------------------------------

;---------------------------------------------
; group.add-bond-description | Group.add_bond_description
;---------------------------------------------

;---------------------------------------------
; group.length | Group.length
;---------------------------------------------

;---------------------------------------------
; group.leftmost-letter | Group.leftmost_letter
; group.rightmost-letter | Group.rightmost_letter
;---------------------------------------------

;---------------------------------------------
; leftmost-in-string?
; rightmost-in-string?
;---------------------------------------------

;---------------------------------------------
; left-neighbor | Group.get_left_neighbor
; right-neighbor | Group.get_right_neighbor
;---------------------------------------------

;---------------------------------------------
; build-group | Workspace.build_group
;---------------------------------------------

;---------------------------------------------
; break-group | Workspace.break_group
;---------------------------------------------

;---------------------------------------------
; top-down-group-scout--category | GroupTopDownCategoryScout
;---------------------------------------------
 
(defun top-down-group-scout--direction 
      (direction-category  
       &aux string chosen-object chosen-bond group-category
            bond-category bond-facet
            opposite-bond-category opposite-direction-category
            direction-to-scan num-of-bonds-to-scan quit
  	    next-bond next-object bond-to-add object-list bond-list
	    i-relevance t-relevance i-unhappiness t-unhappiness)
			      
; This codelet looks for evidence of a group of the given direction.
; Chooses an object, a direction to scan in, and a number 
; of bonds to scan in that direction.  The group-category of the group
; is the associated group-category of the first bond scanned.  (Note that
; for now, this codelet cannot propose groups of only one object.) 
; Scans until no more bonds of the necessary type and direction are found.
; If possible, makes a proposed group of the given direction out of the 
; objects scanned, and posts a group-strength-tester codelet with urgency a 
; function of the degree-of-association of bonds of the given 
; bond-category.

(block nil

  (if* %verbose% 
   then (format t "In top-down-group-scout--direction with direction ~a~&" 
	        (send direction-category :pname)))

  (setq i-relevance (send *initial-string* :local-direction-category-relevance 
			direction-category))
  (setq t-relevance (send *target-string* :local-direction-category-relevance 
			direction-category))

  (setq i-unhappiness (send *initial-string* :intra-string-unhappiness))
  (setq t-unhappiness (send *target-string* :intra-string-unhappiness))

  (if* %verbose% 
   then (format t "About to choose string.  Relevance of ~a is: " 
		(send direction-category :pname))
        (format t "initial string: ~a, target string: ~a~&"
		  i-relevance t-relevance)
	(format t "i-unhappiness: ~a, t-unhappiness: ~a~&"
		  i-unhappiness t-unhappiness))

  (setq string 
	(nth (select-list-position 
		 (list (round (average i-relevance i-unhappiness))
		       (round (average t-relevance t-unhappiness))))
	     (list *initial-string* *target-string*)))
		
  (if* %verbose% then (format t "Chose ~a~&" (send string :pname)))

  ; Choose an object on the workspace by intra-string-salience.
  (setq chosen-object (send string :choose-object ':intra-string-salience))

  (if* %verbose% 
   then (format t "Chose object ") (send chosen-object :print) (format t "~%"))
  
  ; If the object is a group that spans the string, fizzle.
  (if* (send chosen-object :spans-whole-string?)
   then (if* %verbose% 
	 then (format t "This object spans the whole string.  Fizzling.~&"))
        (return))

  ; Now choose a direction in which to scan. 
  (setq direction-to-scan
	(cond ((send chosen-object :leftmost-in-string?) plato-right)
              ((send chosen-object :rightmost-in-string?) plato-left)
	      (t (select-list-item-by-method (list plato-left plato-right) 
	                                     :activation))))

  ; Now choose a number of bonds to scan.
  (setq num-of-bonds-to-scan 
	(select-list-position 
	    (send string :num-of-bonds-to-scan-distribution)))

  (if* %verbose% 
   then (format t "About to scan ~a bonds to the ~a~&" 
		  num-of-bonds-to-scan (send direction-to-scan :pname)))
  
  ; Now get the first bond in that direction.
  (if* (eq direction-to-scan plato-left)
   then (setq chosen-bond (send chosen-object :left-bond))
   else (setq chosen-bond (send chosen-object :right-bond)))

  (if* (null chosen-bond)
   then (if* %verbose% then (format t "No bond in this direction.~&"))
	(return))
     
  (if* %verbose% 
   then (format t "The first bond is: ") 
        (send chosen-bond :print))

  (if* (not (eq (send chosen-bond :direction-category) direction-category))
   then (if* %verbose% 
	 then (format t "Chosen bond has wrong direction.  Fizzling.~&"))
        (return))

  (setq bond-category (send chosen-bond :bond-category))
  (setq bond-facet (send chosen-bond :bond-facet)) 

  (setq opposite-bond-category 
	(send bond-category :get-related-node plato-opposite))
  (setq opposite-direction-category 
	(send direction-category :get-related-node plato-opposite))

  ; Get a list of the objects and bonds.
  ; This assumes that there is at most one bond between any pair of 
  ; objects.  If there are bonds that are opposite in bond category 
  ; and direction to the chosen bond, then add their flipped versions to 
  ; the bond list.
  (setq object-list (list (send chosen-bond :left-obj)
			  (send chosen-bond :right-obj)))
  (setq bond-list (list chosen-bond))
  (setq next-bond chosen-bond)
  (loop for i from 2 to num-of-bonds-to-scan until quit do
        (setq bond-to-add nil)
        (if* (eq direction-to-scan plato-left)
         then (setq next-bond (send next-bond :choose-left-neighbor))
	      (if* (null next-bond) 
	       then (setq quit t) 
	       else (setq next-object (send next-bond :left-obj)))
         else (setq next-bond (send next-bond :choose-right-neighbor))
	      (if* (null next-bond) 
	       then (setq quit t) 
	       else (setq next-object (send next-bond :right-obj))))
	       
        ; Decide whether or not to add bond.
	(cond ((null next-bond) (setq bond-to-add nil))
	      ((and (eq (send next-bond :bond-category) 
			bond-category)
		    (eq (send next-bond :direction-category) 
			direction-category)
		    (eq (send next-bond :bond-facet) bond-facet))
               (setq bond-to-add next-bond))
	      ((and (eq (send next-bond :bond-category) 
			opposite-bond-category)
		    (eq (send next-bond :direction-category) 
			opposite-direction-category)
		    (eq (send next-bond :bond-facet) bond-facet))
	       (setq bond-to-add (send next-bond :flipped-version))))
	      
        (if* bond-to-add
         then (push next-object object-list)
              (push bond-to-add bond-list)
	 else (setq quit t)))
  
  (setq group-category 
	(send bond-category :get-related-node plato-group-category))

  (propose-group object-list bond-list group-category direction-category)))

;---------------------------------------------
; group-scout--whole-string | GroupWholeStringScout
;---------------------------------------------

;---------------------------------------------
; group-strength-tester | GroupStrengthTester
;---------------------------------------------

;---------------------------------------------
; group-builder | GroupBuilder
;---------------------------------------------

;---------------------------------------------
; flipped-version
;---------------------------------------------

;---------------------------------------------
; get-possible-group-bonds | Workspace.possible_group_bonds
;---------------------------------------------

;---------------------------------------------
; group-equal? | Group.__eq__
;---------------------------------------------
