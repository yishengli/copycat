;---------------------------------------------
; workspace-structure.update_strengths
;---------------------------------------------

;---------------------------------------------
; description.calculate-internal-strength
;---------------------------------------------

;---------------------------------------------
; description.calculate-external-strength
;---------------------------------------------

(defmethod (bond :calculate-internal-strength) 
           (&aux member-compatibility-factor bond-facet-factor)
  ; bonds between objects of the same type (letter-letter or 
  ; group-group) are stronger than bonds between different types 
  ; (letter-group or group-letter).					
  (if* (eq (flavor-type from-obj) (flavor-type to-obj))
   then (setq member-compatibility-factor 1)
   else (setq member-compatibility-factor .7))

  ; for now, letter-category bonds are stronger than other types of
  ; bonds (namely, length bonds).  this should be fixed; a 
  ; more general mechanism is needed.	   
  (if* (eq bond-facet plato-letter-category)
   then (setq bond-facet-factor 1)
   else (setq bond-facet-factor .7)) 

  (min 100 (round (* member-compatibility-factor bond-facet-factor
			   (send bond-category 
				 :bond-degree-of-association)))))

;---------------------------------------------

(defmethod (bond :calculate-external-strength) ()
  (send self :local-support))
 
;---------------------------------------------

(defmethod (group :calculate-internal-strength) 
           (&aux bond-facet-factor bond-component 
		 bond-component-weight 
		 length-component length-component-weight)

  ; for now, groups based on letter-category are stronger than groups based
  ; on other facets (namely, length). this should be fixed; a more 
  ; general mechanism is needed.	   
  (if* (eq bond-facet plato-letter-category)
         then (setq bond-facet-factor 1)
         else (setq bond-facet-factor .5))

  (setq bond-component 
	(* (send (send group-category :get-related-node 
		       plato-bond-category) :degree-of-association) 
	   bond-facet-factor))
  
  (setq length-component 
        (cond ((= (send self :length) 1) 5)
	      ((= (send self :length) 2) 20)
	      ((= (send self :length) 3) 60)
	      (t 90)))

  (setq bond-component-weight (expt bond-component .98))
  (setq length-component-weight (fake-reciprocal bond-component-weight))
	      
  (weighted-average `((,bond-component . ,bond-component-weight)
                      (,length-component . ,length-component-weight))))
    
;---------------------------------------------

(defmethod (group :calculate-external-strength)  ()
  (if* (send self :spans-whole-string?) 
   then 100 else (send self :local-support)))

;---------------------------------------------

(defmethod (correspondence :calculate-internal-strength) 
		(&aux relevant-distinguishing-cms 
		     average-strength internal-coherence-factor
		     num-of-concept-mappings-factor num-of-concept-mappings)
; a function of how many concept-mappings there are, how strong they are,
; and how much internal coherence there is among concept mappings.
  (setq relevant-distinguishing-cms
	(send self :relevant-distinguishing-cms))

  (if* (null relevant-distinguishing-cms)
   then 0
   else (setq average-strength
	      (list-average 
		  (send-method-to-list 
		      relevant-distinguishing-cms :strength)))

        (setq num-of-concept-mappings (length relevant-distinguishing-cms))
        (setq num-of-concept-mappings-factor
	      (case num-of-concept-mappings
		    (1 .8)  
		    (2 1.2)
		    (t 1.6)))

        (if* (send self :internally-coherent?)
         then (setq internal-coherence-factor 2.5)
         else (setq internal-coherence-factor 1))

        (min 100 (round (* average-strength internal-coherence-factor
			   num-of-concept-mappings-factor)))))

;---------------------------------------------

(defmethod (correspondence :calculate-external-strength) ()
  (send self :support))

;---------------------------------------------

(defmethod (correspondence :internally-coherent?) 
           (&aux cm-list result)
; for now this returns t if there is any pair of relevant-distinguishing 
; concept-mappings that support each other.  this isn't quite right.
  (setq cm-list
	(send self :relevant-distinguishing-cms))
  (if* (> (length cm-list) 1)
   then (loop for cm in cm-list until result do
	      (loop for other-cm in (remove cm cm-list) 
	            when (supporting-concept-mappings? cm other-cm)
	            return (setq result t))))
  result)
	      
;---------------------------------------------
; rule.calculate-internal-strength
;---------------------------------------------

;---------------------------------------------
; rule.calculate-external-strength
;---------------------------------------------

;---------------------------------------------
; workspace-structure.calculate-total-strength
;---------------------------------------------

;---------------------------------------------
; workspace-structure.total-weakness
;---------------------------------------------

(defmethod (concept-mapping :slippability) (&aux degree-of-association)
; this returns a value representing the ease with which this slippage can be
; made.  conceptual-depth gives a resistance to slippage.
  (setq degree-of-association (send self :degree-of-association))
  (if* (= degree-of-association 100) 
   then 100
   else (* degree-of-association
	   (- 1 (sqr (/ (send self :conceptual-depth) 100))))))

;---------------------------------------------

(defmethod (concept-mapping :strength) (&aux degree-of-association)
; this returns a value representing the strength of the concept-mapping.
; the closer and the more general the nodes, the stronger.  
  (setq degree-of-association (send self :degree-of-association))
  (if* (= degree-of-association 100) 
   then 100
   else (* degree-of-association
	   (+ 1 (sqr (/ (send self :conceptual-depth) 100))))))

;---------------------------------------------

(defun supporting-correspondences? (c1 c2 &aux (result nil))
; returns t if c1 supports c2, nil otherwise.  for now, c1 is 
; defined to support c2 if c1 is not incompatible with c2, and 
; has a concept-mapping that supports the concept-mappings of c2.

  (cond ((or (eq (send c1 :obj1) (send c2 :obj1))	
	     (eq (send c1 :obj2) (send c2 :obj2)))
         (setq result nil))
	((incompatible-correspondences? c1 c2) (setq result nil))
        (t (loop for cm1 in (send c1 :distinguishing-concept-mappings) 
		 until result do
                  (loop for cm2 in (send c2 :distinguishing-concept-mappings)
		        when (supporting-concept-mappings? cm1 cm2) 
			do (setq result t)
			   (return)))))
  result)

;---------------------------------------------

(defun incompatible-correspondences? (c1 c2 &aux (result nil))
; returns t if c1 is incompatible with c2, nil otherwise.  for now, c1 is 
; defined to be incompatible with c2 if c1 and c2 share objects, or c1 has a 
; concept-mapping incompatible with the concept-mappings of c2.


  (if* (or (eq (send c1 :obj1) (send c2 :obj1))	
	  (eq (send c1 :obj2) (send c2 :obj2)))
   then (setq result t)
   else (loop for cm1 in (send c1 :concept-mapping-list) until result do
              (loop for cm2 in (send c2 :concept-mapping-list) 
		    when (incompatible-concept-mappings? cm1 cm2) do
                         (setq result t)
			 (return))))
  result)

;---------------------------------------------

(defun supporting-concept-mappings? (cm1 cm2)
; concept-mappings (a -> b) and (c -> d) support each other if a is related
; to c and if b is related to d and the a -> b relationship is the same as the
; c -> d relationship.  e.g., rightmost -> rightmost supports right -> right 
; and leftmost -> leftmost.  notice that slipnet distances are not looked 
; at, only slipnet links.  this should be changed eventually.

  ; if the two concept-mappings are the same, then return t.  this
  ; means that letter->group supports letter->group, even though these
  ; concept-mappings have no label.
  (cond ((and (eq (send cm1 :descriptor1) (send cm2 :descriptor1))
	      (eq (send cm1 :descriptor2) (send cm2 :descriptor2))) 
	 t)
        ; if the descriptors are not related, then return nil.
        ((not (or (related? (send cm1 :descriptor1) (send cm2 :descriptor1))
 	          (related? (send cm1 :descriptor2) (send cm2 :descriptor2))))
         nil)
        ; if one of the concept-mappings has no label, then return nil.
        ((or (null (send cm1 :label)) (null (send cm2 :label)))
         nil)
        ((eq (send cm1 :label) (send cm2 :label))
         t)
        (t nil)))

;---------------------------------------------

(defun incompatible-concept-mappings? (cm1 cm2)
; concept-mappings (a -> b) and (c -> d) are incompatible if a is 
; related to c or if b is related to d, and the a -> b relationship is 
; different from the c -> d relationship. e.g., rightmost -> leftmost
; is incompatible with right -> right, since rightmost is linked 
; to right, but the relationships (opposite and identity) are different.  
; notice that slipnet distances are not looked at, only slipnet links. this 
; should be changed eventually.
  (if* (not (or (related? (send cm1 :descriptor1) (send cm2 :descriptor1))
 	        (related? (send cm1 :descriptor2) (send cm2 :descriptor2))))
   then nil
   else (if* (or (null (send cm1 :label)) (null (send cm2 :label)))
         then nil
         else (if* (not (eq (send cm1 :label) (send cm2 :label)))
               then t
	       else nil))))

;---------------------------------------------

(defun incompatible-concept-mapping-lists? (l1 l2 &aux incompatible?)
; returns t if the two lists of concept-mappings contain incompatible
; concept-mappings.
  (loop for cm1 in l1
        until incompatible? do
        (loop for cm2 in l2
 	      when (incompatible-concept-mappings? cm1 cm2) do
	           (setq incompatible? t)
	           (return)))
  incompatible?)

;---------------------------------------------
; related? | slipnode.are_related
;---------------------------------------------

;---------------------------------------------
; linked? | slipnode.are_linked
;---------------------------------------------

;---------------------------------------------
; slip-linked? | slipnode.are_slip_linked
;---------------------------------------------

;---------------------------------------------
; slipnode.bond-degree-of-association | slipnode.bond_degree_of_association
;---------------------------------------------

(defmethod (bond :importance) ()
; sameness bonds are more important that other bonds of other 
; categories (for now, the only other categories are predecessor and 
; successor).
  (if* (eq bond-category plato-sameness) 
   then 100 else 50))

;---------------------------------------------

(defmethod (bond :happiness) ()
  (if* group then (send group :total-strength) else 0))

;---------------------------------------------

(defmethod (bond :unhappiness) ()
  (fake-reciprocal (send self :happiness)))

;---------------------------------------------

(defmethod (bond :salience) ()
  (round (average (send self :importance) (send self :unhappiness))))

;---------------------------------------------
; slipnode.local-descriptor-support | slipnode.local_descriptor_support
;---------------------------------------------
  
;---------------------------------------------
; slipnode.local-description-type-support | slipnode.local_description_type_support
;---------------------------------------------

;---------------------------------------------
; slipnode.total-description-type-support | slipnode.total_desription_type_support
;---------------------------------------------

;---------------------------------------------
; description.local-support
;---------------------------------------------

(defmethod (bond :number-of-local-supporting-bonds) 
           (&aux num-of-supporting-bonds)
; Returns the number of supporting bonds in the given bond's string.
; Looks at all the other bonds in the string, counting bonds of the 
; same bond-category and direction-category.  Doesn't take distance into 
; account; all qualifying bonds in the string are counted the same.
  (setq num-of-supporting-bonds 
	(loop for other-bond in (remove self (send string :bond-list)) 
	      when (and (not (= (letter-distance 
				    (send self :left-obj)
		                    (send other-bond :left-obj)) 0))
                        (not (= (letter-distance 
				    (send self :right-obj)
			            (send other-bond :right-obj)) 0))
		        (eq (send other-bond :bond-category) 
			    bond-category)
		        (eq (send other-bond :direction-category) 
			    direction-category))
	      count t into supporting-bond-count
	      finally (return supporting-bond-count)))

  num-of-supporting-bonds)

;---------------------------------------------

(defmethod (bond :local-density)
           (&aux next-obj last-obj next-bond 
		 (slot-sum 0) (support-sum 0))

; Returns a rough measure of the density in the string of bonds of 
; the same bond-category and direction-category as the given bond.  
; This method is used in calculating the external strength of a bond.
; I don't think this method is quite right.  The result depends on which
; right and left neighbors are chosen, which is probabilistic, so it doesn't
; always give the same value.

  ; First loop though left-neighbors.
  (setq last-obj left-obj)
  (setq next-obj (send left-obj :choose-left-neighbor))
  (loop until (null next-obj) do
	(incf slot-sum) ; Add 1 to the number of possible bond slots looked at.
        ; Look at the bond between these two objects.
	(setq next-bond (aref (send string :left-right-bond-array)
			      (send next-obj :string-number)
			      (send last-obj :string-number)))

        (if* (and next-bond 
		  (eq (send next-bond :bond-category) 
		      bond-category)
                  (eq (send next-bond :direction-category) 
		      direction-category))
                 then (incf support-sum))
  	(setq last-obj next-obj)
	(setq next-obj (send next-obj :choose-left-neighbor)))

    
  ; Now loop though right-neighbors.
  (setq last-obj right-obj)
  (setq next-obj (send right-obj :choose-right-neighbor))
  (loop until (null next-obj) do
	(incf slot-sum) ; Add 1 to the number of possible bond slots looked at.
        ; Look at the bond between these two objects.
	(setq next-bond (aref (send string :left-right-bond-array)
			      (send last-obj :string-number)
			      (send next-obj :string-number)))

        (if* (and next-bond
		  (eq (send next-bond :bond-category) 
		      bond-category)
                  (eq (send next-bond :direction-category) 
		      direction-category))
         then (incf support-sum))
	(setq last-obj next-obj)
	(setq next-obj (send next-obj :choose-right-neighbor)))
    
  (if* (= slot-sum 0) 
   then 100 else (round (* 100 (/ support-sum slot-sum)))))
  
;---------------------------------------------

(defmethod (bond :local-support) (&aux number density adjusted-density
					   number-factor)
  (setq number (send self :number-of-local-supporting-bonds))    
  (if* (= number 0)
   then 0
   else (setq density (send self :local-density))
        (setq adjusted-density (* 100 (sqrt (/ density 100))))
        (setq number-factor (min 1 (expt .6 (/ 1 (cube number)))))
        (round (* adjusted-density number-factor))))
	   

;---------------------------------------------

(defmethod (group :number-of-local-supporting-groups) 
           (&aux num-of-supporting-groups)
; Returns the number of supporting groups in the given group's string.
; Looks at all the other groups in the string, counting groups of the 
; same grouup-category and direction-category.  Doesn't take distance into 
; account; all qualifying groups in the string are counted the same.
  (setq num-of-supporting-groups
	(loop for other-group in (remove self (send string :group-list)) 
	      when (and (not (or (subgroup? self other-group)
				 (subgroup? other-group self)
			         (groups-overlap? self other-group)))
  		        (eq (send other-group :group-category) group-category)
		        (eq (send other-group :direction-category) 
			    direction-category))
	      count t into supporting-group-count
	      finally (return supporting-group-count)))

  num-of-supporting-groups)

;---------------------------------------------

(defmethod (group :local-density) 
           (&aux next-obj next-group  
		 (slot-sum 0) (support-sum 0))

; Returns a rough measure of the density in the string of groups of the same 
; group-category and direction-category as the given group.
; This method is used in calculating the external strength of a group.
; I don't think this method is quite right.  The result depends on which
; right and left neighbors are chosen, which is probabilistic, so it doesn't
; always give the same value.
(block nil
  (if* (send self :string-spanning-group?)
   then (return 100))
  
  ; First loop though left-neighbors.
  (setq next-obj (send left-obj :choose-left-neighbor))
  ; If the next object is a letter in a group, then set the next object
  ; to the the group.  I'm not sure that this is the right 
  ; way to do all this; it might need to be fixed.
  (if* (and (typep next-obj 'letter) (send next-obj :group))
   then (setq next-obj (send next-obj :group)))
  (loop until (null next-obj) do
        ; Look at next-obj's group.  Count the next-group only if it doesn't 
	; overlap the original group.  
	(setq next-group (if* (typep next-obj 'letter) then nil else next-obj))
        (incf slot-sum) ; Add 1 to the number of possible group slots looked 
	                ; at.
        (if* (and next-group
                  ; Don't count the group if it overlaps this group.
	          (not (groups-overlap? self next-group))
                  (eq (send next-group :group-category) group-category)
                  (eq (send next-group :direction-category) 
		      direction-category))
	 then (incf support-sum))
	(setq next-obj (send next-obj :choose-left-neighbor)))

  ; Now loop though right-neighbors.
  (setq next-obj (send right-obj :choose-right-neighbor))
  ; If the next object is a letter in a group, then set the next object
  ; to the group.  I'm not sure that this is the right 
  ; way to do all this; it might need to be fixed.
  (if* (and (typep next-obj 'letter) (send next-obj :group))
   then (setq next-obj (send next-obj :group)))
  (loop until (null next-obj) do
        ; Look at next-obj's group.  Count the next-group only if it doesn't 
	; overlap the original group.  
	(setq next-group (if* (typep next-obj 'letter) then nil else next-obj))
        (incf slot-sum) ; Add 1 to the number of possible group slots looked 
	                ; at.
        ; Support-sum gets full weight for same type of group, 0 
        ; weight for null group, and 0 for different type of group.
        (if* (and next-group
                  ; Don't count the group if it overlaps this group.
	          (not (groups-overlap? self next-group))
                  (eq (send next-group :group-category) group-category)
                  (eq (send next-group :direction-category) 
		      direction-category))
	 then (incf support-sum))
	(setq next-obj (send next-obj :choose-right-neighbor)))

  (if* (= slot-sum 0) 
   then 100 else (round (* 100 (/ support-sum slot-sum))))))

;---------------------------------------------

(defmethod (group :local-support) (&aux number density adjusted-density
					   number-factor)
  (setq number (send self :number-of-local-supporting-groups))    
  (if* (= number 0)
   then 0
   else (setq density (send self :local-density))
        (setq adjusted-density (* 100 (sqrt (/ density 100))))
        (setq number-factor (min 1 (expt .6 (/ 1 (cube number)))))
        (round (* adjusted-density number-factor))))
	   
;---------------------------------------------
; correspondence.support | Correspondence.support
;---------------------------------------------

;---------------------------------------------
; local-bond-category-relevance
;---------------------------------------------

;---------------------------------------------
; local-direction-category-relevance
;---------------------------------------------

;---------------------------------------------
; recursive-group-member? | Gropu.is_recursive_member
;---------------------------------------------
